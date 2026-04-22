"""Unit tests for troubleshooting scan workflow scripts."""

from __future__ import annotations

from scripts.troubleshooting_scans.common import build_filename
from scripts.troubleshooting_scans.select_anomalous_scans import anomaly_score


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
