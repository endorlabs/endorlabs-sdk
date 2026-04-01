"""Unit tests for .github/scripts/endor_ci_fetch_scan_findings helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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


def test_finding_to_github_dict() -> None:
    f = MagicMock()
    f.model_dump = MagicMock(return_value={"uuid": "x", "spec": {}})
    assert fetch.finding_to_github_dict(f) == {"uuid": "x", "spec": {}}
    f.model_dump.assert_called_once_with(mode="json")


@patch.dict("os.environ", {}, clear=True)
def test_load_findings_dicts_for_pr_no_namespace() -> None:
    assert fetch.load_findings_dicts_for_pr(repo="o/r", head_sha="sha") == []


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
