"""Unit tests for PackageVersion resolution report helpers."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from endorlabs.workflows.reports.analyze import package_resolution as mod


@pytest.mark.parametrize(
    ("errors", "expected"),
    [
        (
            None,
            {
                "Full Success": "TRUE",
                "Unresolved Success": "TRUE",
                "Resolved Success": "TRUE",
                "Call Graph Success": "TRUE",
            },
        ),
        (
            {"unresolved": {"status_error": "STATUS_ERROR_UNRESOLVED"}},
            {
                "Full Success": "FALSE",
                "Unresolved Success": "FALSE",
                "Resolved Success": "N/A",
                "Call Graph Success": "N/A",
            },
        ),
        (
            {"resolved": {"status_error": "STATUS_ERROR_RESOLVED"}},
            {
                "Full Success": "FALSE",
                "Unresolved Success": "TRUE",
                "Resolved Success": "FALSE",
                "Call Graph Success": "N/A",
            },
        ),
        (
            {"call_graph": {"status_error": "STATUS_ERROR_CALL_GRAPH"}},
            {
                "Full Success": "FALSE",
                "Unresolved Success": "TRUE",
                "Resolved Success": "TRUE",
                "Call Graph Success": "FALSE",
            },
        ),
    ],
)
def test_success_flags_cascade(
    errors: dict[str, Any] | None, expected: dict[str, str]
) -> None:
    assert mod._success_flags(errors) == expected


def test_pick_best_match_prefers_unresolved_over_later_stages() -> None:
    errors = {
        "unresolved": {
            "error_analysis_best_match": {
                "error_category": "CATEGORY_A",
                "matching_rule": "rule-unresolved",
            }
        },
        "resolved": {
            "error_analysis_best_match": {
                "error_category": "CATEGORY_B",
                "matching_rule": "rule-resolved",
            }
        },
    }
    best = mod._pick_best_match(errors)
    assert best["matching_rule"] == "rule-unresolved"


def test_pick_best_match_falls_through_to_call_graph() -> None:
    errors = {
        "call_graph": {
            "error_analysis_best_match": {
                "matching_rule": "rule-cg",
                "fixable": True,
            }
        }
    }
    best = mod._pick_best_match(errors)
    assert best["matching_rule"] == "rule-cg"
    assert best["fixable"] is True


def test_status_field_drops_unspecified_status_error() -> None:
    errors = {"resolved": {"status_error": "STATUS_ERROR_UNSPECIFIED", "target": "pkg"}}
    assert mod._status_field(errors, "resolved", "status_error") == ""
    assert mod._status_field(errors, "resolved", "target") == "pkg"


def test_project_cache_returns_empty_for_blank_uuid() -> None:
    cache = mod.ProjectCache(MagicMock())
    assert cache.get("", "example-tenant.child") == ("", "")


def test_project_cache_caches_and_tolerates_get_failure() -> None:
    client = MagicMock()
    client.Project.get.side_effect = [
        RuntimeError("boom"),
        {
            "meta": {
                "name": "https://github.com/org/repo.git",
                "tags": ["team-a", "team-b"],
            }
        },
    ]
    cache = mod.ProjectCache(client)
    assert cache.get("pv-uuid-1", "example-tenant.child") == ("", "")
    assert cache.get("pv-uuid-1", "example-tenant.child") == ("", "")
    assert client.Project.get.call_count == 1

    name, tags = cache.get("pv-uuid-2", "example-tenant.child")
    assert name == "https://github.com/org/repo.git"
    assert tags == "team-a;team-b"
    assert cache.get("pv-uuid-2", "example-tenant.other") == (
        "https://github.com/org/repo.git",
        "team-a;team-b",
    )
    assert client.Project.get.call_count == 2


def test_build_row_shape_and_counts() -> None:
    client = MagicMock()
    client.Finding.count.side_effect = [3, 7]
    client.DependencyMetadata.count.side_effect = [1, 9]
    client.Project.get.return_value = {
        "meta": {"name": "https://github.com/org/repo.git", "tags": ["alpha"]}
    }

    pv = {
        "uuid": "00000000-0000-4000-8000-000000000001",
        "meta": {"name": "npm://example@1.0.0"},
        "tenant_meta": {"namespace": "example-tenant.child"},
        "spec": {
            "project_uuid": "00000000-0000-4000-8000-0000000000aa",
            "ecosystem": "ECOSYSTEM_NPM",
            "resolution_errors": {
                "resolved": {
                    "status_error": "STATUS_ERROR_RESOLVED",
                    "target": "lodash",
                    "operation": "resolve",
                    "error_analysis_best_match": {
                        "error_category": "CATEGORY_DEPENDENCY",
                        "matching_rule": "missing-lockfile",
                        "fixable": False,
                        "fixable_notes": "add lockfile",
                    },
                }
            },
        },
        "processing_status": {
            "scan_state": "SCAN_STATE_IDLE",
            "scan_time": "2026-01-02T03:04:05Z",
            "analytic_time": "2026-01-02T04:00:00Z",
            "disable_automated_scan": False,
        },
    }

    row = mod.build_row(client, pv, mod.ProjectCache(client))

    assert set(row) == set(mod.CSV_COLUMNS)
    assert row["Namespace"] == "example-tenant.child"
    assert row["PackageVersion UUID"] == "00000000-0000-4000-8000-000000000001"
    assert row["PackageVersion Name"] == "npm://example@1.0.0"
    assert row["PackageVersion Ecosystem"] == "ECOSYSTEM_NPM"
    assert row["Num Approximated Vulns"] == 3
    assert row["Num Vulns"] == 7
    assert row["Num Approximated Dependencies"] == 1
    assert row["Num Dependencies"] == 9
    assert row["Resolution Error Category"] == "CATEGORY_DEPENDENCY"
    assert row["Resolution Error Type"] == "missing-lockfile"
    assert row["Fixable"] == "FALSE"
    assert row["Fixable Notes"] == "add lockfile"
    assert row["Full Success"] == "FALSE"
    assert row["Unresolved Success"] == "TRUE"
    assert row["Resolved Success"] == "FALSE"
    assert row["Call Graph Success"] == "N/A"
    assert row["Resolution Error (Resolved)"] == "STATUS_ERROR_RESOLVED"
    assert row["Resolution Error Target (Resolved)"] == "lodash"
    assert row["Project Name"] == "https://github.com/org/repo.git"
    assert row["Project Tags"] == "alpha"
    assert row["Endor URL"].endswith(
        "/t/example-tenant.child/projects/"
        "00000000-0000-4000-8000-0000000000aa/versions/default/inventory/packages"
    )
    assert row["Disable Automated Scan"] == "FALSE"


def test_build_summary_aggregates(tmp_path: Path) -> None:
    rows = [
        {
            "Namespace": "example-tenant.a",
            "Full Success": "TRUE",
            "Unresolved Success": "TRUE",
            "Resolved Success": "TRUE",
            "Call Graph Success": "TRUE",
            "Resolution Error Type": "",
        },
        {
            "Namespace": "example-tenant.b",
            "Full Success": "FALSE",
            "Unresolved Success": "FALSE",
            "Resolved Success": "N/A",
            "Call Graph Success": "N/A",
            "Resolution Error Type": "rule-x",
        },
        {
            "Namespace": "example-tenant.b",
            "Full Success": "FALSE",
            "Unresolved Success": "TRUE",
            "Resolved Success": "FALSE",
            "Call Graph Success": "N/A",
            "Resolution Error Type": "",
        },
    ]
    csv_path = tmp_path / "out.csv"
    summary = mod.build_summary("example-tenant", rows, csv_path)
    assert summary["tenant"] == "example-tenant"
    assert summary["row_count"] == 3
    assert summary["namespaces"] == ["example-tenant.a", "example-tenant.b"]
    assert summary["full_success_count"] == 1
    assert summary["full_failure_count"] == 2
    assert summary["unresolved_manifest_false"] == 1
    assert summary["dependency_resolution_false"] == 1
    assert summary["reachability_false"] == 0
    assert summary["no_best_match"] == 1


def test_write_csv_uses_stable_columns(tmp_path: Path) -> None:
    rows = [
        {
            "Namespace": "example-tenant.child",
            "PackageVersion UUID": "00000000-0000-4000-8000-000000000001",
            "PackageVersion Name": "npm://example@1.0.0",
            "Full Success": "TRUE",
            "extra_ignored": "nope",
        }
    ]
    out = tmp_path / "package-resolution.csv"
    mod.write_csv(rows, out)
    with out.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == mod.CSV_COLUMNS
        written = list(reader)
    assert len(written) == 1
    assert written[0]["Namespace"] == "example-tenant.child"
    assert written[0]["Full Success"] == "TRUE"
    assert "extra_ignored" not in written[0]
