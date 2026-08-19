"""Unit tests for troubleshooting scan workflow helpers."""

from __future__ import annotations

from endorlabs.workflows.projects.discovery import duplicate_project_decision
from endorlabs.workflows.troubleshooting_scans.build_scan_pair import (
    _resolve_scan_uuid,
)
from endorlabs.workflows.troubleshooting_scans.common import (
    build_filename,
    date_window_from_bounds,
    extract_scan_mode,
    parse_app_scan_history_url,
    parse_endor_app_url,
    scan_result_extended_summary,
    scan_result_metrics,
    scanlog_entries_have_content,
    scanlog_line_has_content,
)
from endorlabs.workflows.troubleshooting_scans.diff_scans import compute_diff
from endorlabs.workflows.troubleshooting_scans.select_anomalous_scans import (
    anomaly_score,
)


def test_build_filename_uses_required_segments() -> None:
    filename = build_filename(
        root_tenant_name="tenant.example.child",
        object_kind="scan_diff",
        object_uuid="abc123",
        purpose="report",
        extension=".json",
        timestamped=False,
    )
    assert filename.startswith("tenant.example.child__scan_diff__abc123__report")
    assert filename.endswith(".json")


def test_anomaly_score_detects_dependency_collapse() -> None:
    current = {
        "status": "STATUS_PARTIAL_SUCCESS",
        "scan_success": 0,
        "scan_failures": 6,
        "dependency_count_total": 0,
        "findings_critical": 0,
        "findings_high": 0,
        "findings_medium": 0,
        "findings_low": 0,
    }
    previous = {
        "status": "STATUS_PARTIAL_SUCCESS",
        "scan_success": 6,
        "scan_failures": 0,
        "dependency_count_total": 335,
        "findings_critical": 1,
        "findings_high": 2,
        "findings_medium": 3,
        "findings_low": 4,
    }
    score, reasons = anomaly_score(
        current=current,
        previous=previous,
        min_delta_findings=1,
        min_delta_deps=50,
    )
    assert score > 0
    assert "scan_success_drop_to_zero" in reasons
    assert any("dependency_count_total_delta" in reason for reason in reasons)


def test_parse_endor_app_url_project_findings() -> None:
    info = parse_endor_app_url(
        "https://app.endorlabs.com/t/acme.ns.child/projects/69e0a22709f675ea1fd80476"
        "/versions/default/findings?filter.values=%7B%7D"
    )
    assert info["kind"] == "project"
    assert info["project_uuid"] == "69e0a22709f675ea1fd80476"
    assert info["namespace"] == "acme.ns.child"


def test_parse_endor_app_url_scan_history() -> None:
    info = parse_endor_app_url(
        "https://app.endorlabs.com/t/acme.ns/scan-history/69e7d564f391c87dbcba85b2"
    )
    assert info["kind"] == "scan_history"
    assert info["namespace"] == "acme.ns"
    assert info["scan_result_uuid"] == "69e7d564f391c87dbcba85b2"


def test_parse_app_scan_history_url_strips_query() -> None:
    ns, su = parse_app_scan_history_url(
        "https://app.endorlabs.com/t/acme.team.child/scan-history/69e7d564f391c87dbcba85b2"
        "?return_to=%2Ffoo&resourceDetail=%7B%7D"
    )
    assert ns == "acme.team.child"
    assert su == "69e7d564f391c87dbcba85b2"


def test_date_window_explicit_bounds() -> None:
    fd, td = date_window_from_bounds(
        from_date="2025-01-01T00:00:00Z",
        to_date="2025-02-01T00:00:00Z",
        days=None,
    )
    assert fd.startswith("2025-01-01")
    assert td.startswith("2025-02-01")


def test_duplicate_project_decision_limits() -> None:
    ok, warns, err = duplicate_project_decision([{"uuid": "a"}], max_auto=3)
    assert ok
    assert err is None
    assert warns == []

    ok2, _warns2, err2 = duplicate_project_decision([1, 2, 3, 4], max_auto=3)
    assert not ok2
    assert err2 is not None
    assert "too_many" in err2

    ok3, warns3, err3 = duplicate_project_decision([1, 2], max_auto=3)
    assert ok3
    assert err3 is None
    assert warns3


def test_scan_result_extended_summary_minimal() -> None:
    raw = {
        "uuid": "sr1",
        "meta": {"parent_uuid": "p1", "create_time": "2025-01-01T00:00:00Z"},
        "tenant_meta": {"namespace": "example-tenant"},
        "spec": {
            "status": "STATUS_SUCCESS",
            "type": "TYPE_ALL_SCANS",
            "start_time": "2025-01-01T00:00:00Z",
            "end_time": "2025-01-01T01:00:00Z",
            "stats": {"dependency_count_total": 10, "call_graph_errors": 1},
            "environment": {
                "arch": "amd64",
                "os": "linux",
                "endorctl_version": "1.2.3",
                "num_cpus": 4,
                "memory": 8e9,
                "config": {"ScanConfig": {"Enables": ["git"]}},
            },
            "versions": [{"ref": "main", "sha": "abc"}],
        },
    }
    s = scan_result_extended_summary(raw)
    assert s["uuid"] == "sr1"
    assert s["dependency_count_total"] == 10
    assert s["environment"]["num_cpus"] == 4
    assert s["duration_seconds"] == 3600.0
    assert s["stats"]["call_graph_errors"] == 1
    assert "ScanConfig" in s["environment"]["config_summary"]
    assert s["scan_execution"] == "unknown"
    assert s["scan_mode"]["enables"] == ["git"]
    assert s["scan_mode"]["endorctl_flags"] == []


def test_extract_scan_mode_cli_quick_scan_and_local_cache() -> None:
    raw = {
        "uuid": "sr-cli",
        "spec": {
            "environment": {
                "config": {
                    "Command": "scan",
                    "RunBySystem": False,
                    "BypassHostCheck": True,
                    "Verbose": True,
                    "ScanConfig": {
                        "QuickScan": True,
                        "UseLocalCache": True,
                        "AsDefaultBranch": True,
                        "DisablePrivatePackageAnalysis": True,
                        "Enables": ["git", "analytics"],
                        "Path": ".",
                        "ExcludePath": ["target/**"],
                    },
                }
            }
        },
    }
    mode = extract_scan_mode(raw)
    assert mode["scan_execution"] == "CLI"
    assert mode["run_by_system"] is False
    assert mode["quick_scan"] is True
    assert mode["use_local_repo_cache"] is True
    assert mode["command"] == "scan"
    assert "--quick-scan" in mode["endorctl_flags"]
    assert "--use-local-repo-cache" in mode["endorctl_flags"]
    assert "--exclude-path=target/**" in mode["endorctl_flags"]
    assert "--dependencies" not in mode["endorctl_flags"]
    metrics = scan_result_metrics(raw)
    assert metrics["scan_execution"] == "CLI"
    assert metrics["quick_scan"] is True
    assert metrics["scan_mode"]["enables"] == ["git", "analytics"]


def test_extract_scan_mode_cloud_scan() -> None:
    raw = {
        "spec": {
            "environment": {
                "config": {
                    "Command": "scan",
                    "RunBySystem": True,
                    "ScanConfig": {"QuickScan": False},
                }
            }
        }
    }
    mode = extract_scan_mode(raw)
    assert mode["scan_execution"] == "Cloud Scan"
    assert mode["run_by_system"] is True
    assert mode["quick_scan"] is False
    assert "--quick-scan" not in mode["endorctl_flags"]


def test_compute_diff_includes_quick_scan() -> None:
    primary = {
        "uuid": "a",
        "spec": {
            "status": "STATUS_PARTIAL_SUCCESS",
            "environment": {
                "config": {
                    "RunBySystem": False,
                    "ScanConfig": {"QuickScan": True, "UseLocalCache": True},
                }
            },
        },
    }
    secondary = {
        "uuid": "b",
        "spec": {
            "status": "STATUS_SUCCESS",
            "environment": {
                "config": {
                    "RunBySystem": True,
                    "ScanConfig": {"QuickScan": False, "UseLocalCache": False},
                }
            },
        },
    }
    diff = compute_diff(primary, secondary)
    assert diff["changes"]["scan_execution"]["primary"] == "CLI"
    assert diff["changes"]["scan_execution"]["secondary"] == "Cloud Scan"
    assert diff["changes"]["quick_scan"]["primary"] is True
    assert diff["changes"]["quick_scan"]["secondary"] is False
    assert diff["changes"]["use_local_repo_cache"]["primary"] is True


def test_scanlog_line_has_content_embedded_json() -> None:
    line = '{"level":"error","msg":"Unable to resolve dependencies","ts":1}'
    assert scanlog_line_has_content(line)


def test_scanlog_line_has_content_hollow_api_row() -> None:
    line = "2026-07-06 03:16:57.423892+00:00 [UNKNOWN] "
    assert not scanlog_line_has_content(line)


def test_scanlog_entries_have_content_mixed() -> None:
    entries = [
        "2026-07-06 03:16:57.423892+00:00 [UNKNOWN] ",
        '{"level":"error","msg":"checkout failed","ts":1}',
    ]
    assert scanlog_entries_have_content(entries)


def test_resolve_scan_uuid_from_url() -> None:
    url = (
        "https://app.endorlabs.com/t/acme.ns/scan-history/"
        "69e7d564f391c87dbcba85b2?return_to=%2Ffoo"
    )
    assert _resolve_scan_uuid(url=url, uuid=None, label="primary") == (
        "69e7d564f391c87dbcba85b2"
    )
