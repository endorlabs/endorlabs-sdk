"""Unit tests for analytics remediation analysis."""

from __future__ import annotations

from endorlabs.workflows.analytics.remediation import (
    analyze_intra_minor_remediation,
    flatten_intra_minor_usage,
    usage_rows_to_version_counts,
)


def test_flatten_intra_minor_collapses_patch_lines() -> None:
    rows = [
        {"package_version": "2.15.2", "usage_count": 10},
        {"package_version": "2.15.4", "usage_count": 5},
        {"package_version": "2.9.7", "usage_count": 3},
        {"package_version": "2.9.8", "usage_count": 7},
    ]
    counts = usage_rows_to_version_counts(rows)
    flat = flatten_intra_minor_usage(counts)
    assert len(counts) == 4
    assert len(flat) == 2
    by_version = dict(flat)
    assert by_version["2.15.4"] == 15
    assert by_version["2.9.8"] == 10


def test_cve_2018_19362_remediation_comparison() -> None:
    rows = [
        {"package_version": "2.9.7", "usage_count": 9},
        {"package_version": "2.9.8", "usage_count": 191},
        {"package_version": "2.15.2", "usage_count": 100},
    ]
    result = analyze_intra_minor_remediation(
        rows,
        cve_id="CVE-2018-19362",
        package_name="mvn://com.fasterxml.jackson.core:jackson-databind",
    )
    assert result.as_is.version_cardinality == 3
    assert result.as_is.vulnerable_distinct_versions == 1
    assert result.flattened.version_cardinality == 2
    assert result.flattened.vulnerable_distinct_versions == 0
    assert result.flattened.upgrade_paths_to_fix == 0
    payload = result.to_dict()
    assert payload["delta"]["upgrade_paths_to_fix"] == 1
