"""Unit tests for troubleshooting scan workflow helpers."""

from __future__ import annotations

from endorlabs.workflows.troubleshooting_scans.common import (
    build_filename,
    date_window_from_bounds,
    duplicate_project_decision,
    parse_app_scan_history_url,
    parse_endor_app_url,
    scan_result_extended_summary,
)
from endorlabs.workflows.troubleshooting_scans.select_anomalous_scans import (
    anomaly_score,
)


def test_build_filename_uses_required_segments() -> None:
    filename = build_filename(
        root_tenant_name="datavant.apixio-commercial",
        object_kind="scan_diff",
        object_uuid="abc123",
        purpose="report",
        extension=".json",
        timestamped=False,
    )
    assert filename.startswith("datavant.apixio-commercial__scan_diff__abc123__report")
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
        "tenant_meta": {"namespace": "t.ns"},
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
