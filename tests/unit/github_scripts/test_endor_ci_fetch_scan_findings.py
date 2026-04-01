"""Unit tests for .github/scripts/endor_ci_fetch_scan_findings helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from endorlabs.resources.scan_result import ScanResultSpecType

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


def test_extract_ci_run_uuid_from_execution_id() -> None:
    env = MagicMock()
    env.config = {"ExecutionID": "  ex-123  "}
    spec = MagicMock()
    spec.environment = env
    assert fetch.extract_ci_run_uuid_from_scan_result(spec) == "ex-123"


def test_extract_ci_run_uuid_missing() -> None:
    assert fetch.extract_ci_run_uuid_from_scan_result(None) is None
    spec = MagicMock()
    spec.environment = None
    assert fetch.extract_ci_run_uuid_from_scan_result(spec) is None


def test_list_findings_for_ci_run_calls_finding_list() -> None:
    f1 = MagicMock()
    f1.model_dump = MagicMock(return_value={"uuid": "a"})
    mock_client = MagicMock()
    mock_client.Finding.list.return_value = [f1]
    out = fetch.list_findings_for_ci_run(
        mock_client,
        ci_run_uuid="cid",
        namespace="ns.x",
        max_findings=10,
    )
    assert out == [{"uuid": "a"}]
    mock_client.Finding.list.assert_called_once()
    lp = mock_client.Finding.list.call_args.kwargs["list_params"]
    assert lp.ci_run_uuid == "cid"


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
