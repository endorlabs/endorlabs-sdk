"""Unit tests for report packet parity helpers."""

from __future__ import annotations

from endorlabs.workflows.reports.parity import (
    compare_findings_burndown,
    compare_onboarding,
    compare_packet_cube,
    compare_sprawl,
)


def test_compare_onboarding_exact() -> None:
    rows = compare_onboarding(
        {
            "allRegistrations": 100,
            "distinctRepositories": 80,
            "duplicateRegistrations": 5,
        },
        {"raw_count": 100, "unique_by_name": 80, "duplicate_extra": 5},
    )
    assert all(r.within_tolerance for r in rows)


def test_compare_sprawl_maps_packages_to_p() -> None:
    rows = compare_sprawl(
        {"estate": {"all": {"all": {"p": 10, "v": 25, "max": 4}}}},
        {"estate": {"all": {"all": {"packages": 10, "versions": 25, "max": 4}}}},
    )
    assert all(r.within_tolerance for r in rows)


def test_compare_findings_burndown_gap_end_exact() -> None:
    cell = {"gapEnd": 42}
    nested = {"perPath": {"all": {"all": {"all": cell}}}}
    rows = compare_findings_burndown(
        {
            "seriesFilters": nested,
            "throughput": {
                "perPath": {"all": {"mainScans91d": 100, "ciRunScans21d": 20}}
            },
        },
        {
            "seriesFilters": nested,
            "throughput": {
                "perPath": {"all": {"mainScans91d": 99, "ciRunScans21d": 19}}
            },
            "tagSeries": {"tags": ["a", "b"]},
        },
        tag_catalog_count=2,
    )
    gap = next(r for r in rows if r.metric == "burndown.gapEnd.all/all/all")
    assert gap.within_tolerance and gap.new == 42 and gap.prior == 42


def test_compare_packet_cube_fixture_slice() -> None:
    cube = {
        "tagCatalog": [{"tag": "team-alpha"}],
        "reports": {
            "onboarding": {
                "allRegistrations": 50,
                "distinctRepositories": 40,
                "duplicateRegistrations": 2,
            },
            "versionSprawl": {"estate": {"all": {"all": {"p": 5, "v": 8, "max": 3}}}},
            "findingsBurndown": {
                "seriesFilters": {"perPath": {"all": {"all": {"all": {"gapEnd": 7}}}}},
                "throughput": {
                    "perPath": {"all": {"mainScans91d": 10, "ciRunScans21d": 2}}
                },
            },
        },
    }
    report = compare_packet_cube(
        cube,
        baseline_adoption={
            "raw_count": 50,
            "unique_by_name": 40,
            "duplicate_extra": 2,
        },
        baseline_sprawl={
            "estate": {"all": {"all": {"packages": 5, "versions": 8, "max": 3}}}
        },
        baseline_burndown={
            "seriesFilters": {"perPath": {"all": {"all": {"all": {"gapEnd": 7}}}}},
            "throughput": {
                "perPath": {"all": {"mainScans91d": 10, "ciRunScans21d": 2}}
            },
            "tagSeries": {"tags": ["team-alpha"]},
        },
    )
    assert report.ok
