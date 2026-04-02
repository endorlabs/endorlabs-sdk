"""Unit tests for .github/scripts/endor_ci_fetch_scan_findings helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from endorlabs.resources.scan_result import ScanResultSpecStatus, ScanResultSpecType

_SCRIPTS = Path(__file__).resolve().parents[3] / ".github" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import endor_ci_fetch_scan_findings as fetch


def test_github_repo_url_variants() -> None:
    assert fetch.github_repo_url_variants("a/b") == [
        "https://github.com/a/b.git",
        "https://github.com/a/b",
    ]
    assert fetch.github_repo_url_variants("") == []
    assert fetch.github_repo_url_variants("nope") == []


def test_finding_uuids_from_scan_result_prefers_findings() -> None:
    spec = MagicMock()
    spec.findings = ["u1", "u2", "u1"]
    spec.blocking_findings = ["b1"]
    spec.warning_findings = None
    assert fetch.finding_uuids_from_scan_result(spec) == ["u1", "u2"]


def test_finding_uuids_from_scan_result_fallback_blocking_warning() -> None:
    spec = MagicMock()
    spec.findings = []
    spec.blocking_findings = ["b1", "b1"]
    spec.warning_findings = ["w1"]
    assert fetch.finding_uuids_from_scan_result(spec) == ["b1", "w1"]


def test_pick_scan_result_matches_sha() -> None:
    v_match = MagicMock(sha="abc123")
    v_other = MagicMock(sha="deadbeef")
    spec_new = MagicMock(versions=[v_other])
    spec_old = MagicMock(versions=[v_match])
    new_sr = MagicMock()
    new_sr.spec = spec_new
    old_sr = MagicMock()
    old_sr.spec = spec_old
    picked = fetch.pick_scan_result([new_sr, old_sr], "ABC123")
    assert picked is old_sr


def test_pick_scan_result_newest_when_no_sha_match() -> None:
    v = MagicMock(sha="zzz")
    spec = MagicMock(versions=[v])
    first = MagicMock()
    first.spec = spec
    second = MagicMock()
    second.spec = spec
    assert fetch.pick_scan_result([first, second], "nomatch") is first


def test_pick_scan_result_prefers_pr_security_review_when_sha_matches_both() -> None:
    v = MagicMock(sha="shared")
    spec_all = MagicMock(versions=[v], type=ScanResultSpecType.ALL_SCANS)
    spec_pr = MagicMock(versions=[v], type=ScanResultSpecType.PR_SECURITY_REVIEW)
    sr_all = MagicMock()
    sr_all.spec = spec_all
    sr_pr = MagicMock()
    sr_pr.spec = spec_pr
    picked = fetch.pick_scan_result([sr_all, sr_pr], "shared")
    assert picked is sr_pr


def _mk_repo_version(*, uuid: str, ref: str = "", sha: str = "") -> MagicMock:
    rv = MagicMock()
    rv.uuid = uuid
    version = MagicMock(ref=ref, sha=sha)
    rv.spec = MagicMock(version=version)
    return rv


def test_resolve_repository_version_prefers_hint_uuid() -> None:
    versions = [
        _mk_repo_version(uuid="rv-1", ref="feature/a", sha="111"),
        _mk_repo_version(uuid="rv-2", ref="feature/b", sha="222"),
    ]
    picked, strategy = fetch.resolve_repository_version(
        versions,
        head_sha="222",
        head_ref="feature/b",
        repository_version_hint="rv-1",
    )
    assert picked is versions[0]
    assert strategy == "hint:uuid"


def test_resolve_repository_version_prefers_sha_then_ref() -> None:
    versions = [
        _mk_repo_version(uuid="rv-1", ref="feature/a", sha="111"),
        _mk_repo_version(uuid="rv-2", ref="feature/b", sha="222"),
    ]
    picked, strategy = fetch.resolve_repository_version(
        versions,
        head_sha="222",
        head_ref="feature/a",
        repository_version_hint=None,
    )
    assert picked is versions[1]
    assert strategy == "sha"


def test_refs_loosely_equal_branch_and_refs_heads() -> None:
    assert fetch._refs_loosely_equal("refs/heads/my-feat", "my-feat")
    assert fetch._refs_loosely_equal("MY-FEAT", "my-feat")
    assert not fetch._refs_loosely_equal("my-feat", "other")


def test_resolve_repository_version_ref_matches_refs_heads_prefix() -> None:
    versions = [
        _mk_repo_version(uuid="rv-1", ref="refs/heads/feature/a", sha="111"),
    ]
    picked, strategy = fetch.resolve_repository_version(
        versions,
        head_sha="",
        head_ref="feature/a",
        repository_version_hint=None,
    )
    assert picked is versions[0]
    assert strategy == "ref"


def test_resolve_repository_version_ref_fallback() -> None:
    versions = [
        _mk_repo_version(uuid="rv-1", ref="feature/a", sha="111"),
        _mk_repo_version(uuid="rv-2", ref="feature/b", sha="222"),
    ]
    picked, strategy = fetch.resolve_repository_version(
        versions,
        head_sha="missing",
        head_ref="feature/b",
        repository_version_hint=None,
    )
    assert picked is versions[1]
    assert strategy == "ref"


def test_scan_results_matching_repository_version_returns_all_matches() -> None:
    rv = _mk_repo_version(uuid="rv-1", ref="feature/a", sha="abc")
    v = MagicMock(ref="feature/a", sha="abc")
    spec_a = MagicMock(versions=[v], type=ScanResultSpecType.ALL_SCANS)
    spec_pr = MagicMock(versions=[v], type=ScanResultSpecType.PR_SECURITY_REVIEW)
    sr_a = MagicMock()
    sr_a.spec = spec_a
    sr_pr = MagicMock()
    sr_pr.spec = spec_pr
    got = fetch.scan_results_matching_repository_version(
        [sr_a, sr_pr],
        repository_version=rv,
        head_sha="abc",
        head_ref="feature/a",
    )
    assert sr_a in got
    assert sr_pr in got
    assert len(got) == 2


def test_list_finding_uuids_for_repository_version_caps_and_dedupes() -> None:
    rv = _mk_repo_version(uuid="rv-u1", ref="x", sha="y")
    f1 = MagicMock(uuid="u1")
    f2 = MagicMock(uuid="u2")
    mock_client = MagicMock()
    mock_client.Finding.list.return_value = [f1, f2]
    out = fetch.list_finding_uuids_for_repository_version(
        mock_client, rv, namespace="ns", max_findings=500
    )
    assert out == ["u1", "u2"]
    lp = mock_client.Finding.list.call_args.kwargs["list_params"]
    assert 'meta.parent_uuid=="rv-u1"' in lp.filter


def test_union_finding_uuids_from_scan_results_dedupes() -> None:
    s1 = MagicMock()
    s1.spec = MagicMock(
        findings=["a", "b"], blocking_findings=None, warning_findings=None
    )
    s2 = MagicMock()
    s2.spec = MagicMock(
        findings=["b", "c"], blocking_findings=None, warning_findings=None
    )
    assert fetch.union_finding_uuids_from_scan_results([s1, s2]) == ["a", "b", "c"]


def test_pick_scan_result_for_repository_version_prefers_pr_review_type() -> None:
    rv = _mk_repo_version(uuid="rv-1", ref="feature/a", sha="abc")
    v = MagicMock(ref="feature/a", sha="abc")
    spec_all = MagicMock(versions=[v], type=ScanResultSpecType.ALL_SCANS)
    spec_pr = MagicMock(versions=[v], type=ScanResultSpecType.PR_SECURITY_REVIEW)
    sr_all = MagicMock()
    sr_all.spec = spec_all
    sr_pr = MagicMock()
    sr_pr.spec = spec_pr
    picked = fetch.pick_scan_result_for_repository_version(
        [sr_all, sr_pr],
        repository_version=rv,
        head_sha="abc",
        head_ref="feature/a",
    )
    assert picked is sr_pr


def test_finding_to_github_dict() -> None:
    f = MagicMock()
    f.model_dump = MagicMock(return_value={"uuid": "x", "spec": {}})
    assert fetch.finding_to_github_dict(f) == {"uuid": "x", "spec": {}}
    f.model_dump.assert_called_once_with(mode="json")


@patch.dict("os.environ", {}, clear=True)
def test_load_findings_dicts_for_pr_no_namespace() -> None:
    assert fetch.load_findings_dicts_for_pr(repo="o/r", head_sha="sha") == []


def test_list_scan_results_for_project_sorts_without_server_sort() -> None:
    mock_client = MagicMock()
    older = MagicMock()
    older.meta = MagicMock(create_time="2020-01-01T00:00:00Z")
    newer = MagicMock()
    newer.meta = MagicMock(create_time="2021-01-01T00:00:00Z")
    mock_client.ScanResult.list.return_value = [older, newer]
    out = fetch.list_scan_results_for_project(
        mock_client, "proj-uuid", namespace="ns.test"
    )
    assert out == [newer, older]
    lp = mock_client.ScanResult.list.call_args.kwargs["list_params"]
    assert lp.sort_by is None


@patch("endor_ci_fetch_scan_findings.time.sleep")
@patch("endor_ci_fetch_scan_findings.time.monotonic")
def test_wait_for_scan_result_ready_timeout_when_still_running_returns_empty(
    mock_mono: MagicMock, mock_sleep: MagicMock
) -> None:
    # monotonic: deadline base, while-check, sleep_for calc, next while-check
    mock_mono.side_effect = [0.0, 0.0, 0.0, 999.0]
    v = MagicMock(sha="abc")
    spec = MagicMock(versions=[v], status=ScanResultSpecStatus.RUNNING)
    sr = MagicMock()
    sr.spec = spec
    mock_client = MagicMock()
    with patch.object(fetch, "list_scan_results_for_project", return_value=[sr]):
        out = fetch.wait_for_scan_result_ready(
            mock_client, "proj", "abc", namespace="ns", timeout_sec=60.0
        )
    assert out == []


@patch("endor_ci_fetch_scan_findings.time.sleep")
@patch("endor_ci_fetch_scan_findings.time.monotonic")
def test_wait_for_scan_result_ready_returns_immediately_when_terminal(
    mock_mono: MagicMock, mock_sleep: MagicMock
) -> None:
    mock_mono.side_effect = [0.0, 0.0]
    v = MagicMock(sha="abc")
    spec = MagicMock(versions=[v], status=ScanResultSpecStatus.SUCCESS)
    sr = MagicMock()
    sr.spec = spec
    mock_client = MagicMock()
    with patch.object(fetch, "list_scan_results_for_project", return_value=[sr]):
        out = fetch.wait_for_scan_result_ready(
            mock_client, "proj", "abc", namespace="ns", timeout_sec=300.0
        )
    assert out == [sr]


def test_sort_scan_results_newest_first() -> None:
    old = MagicMock()
    old.meta = MagicMock(create_time="2024-01-01T00:00:00Z")
    new = MagicMock()
    new.meta = MagicMock(create_time="2025-06-01T12:00:00Z")
    no_time = MagicMock()
    no_time.meta = MagicMock(create_time=None)
    out = fetch._sort_scan_results_newest_first([no_time, old, new])
    assert out[0] is new
    assert out[1] is old
    assert out[2] is no_time


@patch("endor_ci_fetch_scan_findings.endorlabs.Client")
def test_load_findings_dicts_for_pr_no_project(mock_client_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client_cls.return_value = mock_client
    mock_client_cls.side_effect = None
    with patch.object(fetch, "find_project_by_repo", return_value=None):
        out = fetch.load_findings_dicts_for_pr(
            repo="o/r", head_sha="abc", tenant="t.ns"
        )
    assert out == []


@patch("endor_ci_fetch_scan_findings.endorlabs.Client")
def test_load_findings_dicts_for_pr_hydrates_scan_result_findings(
    mock_client_cls: MagicMock,
) -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client_cls.return_value = mock_client

    project = MagicMock()
    project.uuid = "proj-1"
    project.tenant_meta = MagicMock(namespace="ns.test")

    picked_scan = MagicMock()
    picked_scan.uuid = "scan-1"
    picked_scan.spec = MagicMock(
        findings=["f-1"],
        blocking_findings=None,
        warning_findings=None,
        status=ScanResultSpecStatus.SUCCESS,
        versions=[MagicMock(sha="abc")],
    )

    with (
        patch.object(fetch, "find_project_by_repo", return_value=project),
        patch.object(fetch, "list_repository_versions_for_project", return_value=[]),
        patch.object(fetch, "resolve_repository_version", return_value=(None, "none")),
        patch.object(fetch, "wait_for_scan_result_ready", return_value=[picked_scan]),
        patch.object(fetch, "hydrate_findings", return_value=[{"uuid": "f-1"}]),
    ):
        out = fetch.load_findings_dicts_for_pr(
            repo="o/r",
            head_sha="abc",
            head_ref="feature/a",
            tenant="t.ns",
        )
    assert out == [{"uuid": "f-1"}]
