"""Unit tests for onboarding ScanResult cadence helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from endorlabs.workflows.reports.analyze.onboarding_cadence import (
    ci_filter,
    main_full_filter,
    main_with_analytics_filter,
    rank_projects,
    redistribute_by_tag,
)
from endorlabs.workflows.reports.export.csv.packet_exports import (
    onboarding_cadence_by_project_rows,
    onboarding_cadence_by_tag_rows,
    onboarding_cadence_weekly_rows,
)
from endorlabs.workflows.reports.export.html.render import _render_onboarding


def test_cadence_filter_builders() -> None:
    window = "meta.create_time>=date(2026-01-01T00:00:00Z)"
    assert "TYPE_ALL_SCANS" in main_full_filter(window)
    assert "CONTEXT_TYPE_MAIN" in main_full_filter(window)
    assert "TYPE_ALL_SCANS" not in main_with_analytics_filter(window)
    assert "CONTEXT_TYPE_CI_RUN" in ci_filter(window)


def test_redistribute_by_tag_ranks() -> None:
    by_project = {
        "a": {"mainFullScans": 10, "ciScans": 1},
        "b": {"mainFullScans": 5, "ciScans": 5},
        "c": {"mainFullScans": 0, "ciScans": 2},
    }
    catalog = [
        {"tag": "team-b", "projectCount": 2, "projectUuids": ["b", "c"]},
        {"tag": "team-a", "projectCount": 1, "projectUuids": ["a"]},
    ]
    rows = redistribute_by_tag(by_project, catalog)
    assert rows[0]["tag"] == "team-a"
    assert rows[0]["mainFullScans"] == 10
    assert rows[1]["tag"] == "team-b"
    assert rows[1]["mainFullScans"] == 5
    assert rows[1]["ciScans"] == 7
    assert rows[1]["mainPerProject"] == 2.5


def test_rank_projects() -> None:
    by_project = {
        "a": {"mainFullScans": 1, "ciScans": 9},
        "b": {"mainFullScans": 8, "ciScans": 0},
    }
    projects = [
        {
            "uuid": "a",
            "name": "https://github.com/org/a.git",
            "namespace": "example-tenant",
            "tags": [],
        },
        {
            "uuid": "b",
            "name": "https://github.com/org/b.git",
            "namespace": "example-tenant.child",
            "tags": ["x"],
        },
    ]
    top = rank_projects(by_project, projects, limit=1)
    assert len(top) == 1
    assert top[0]["uuid"] == "b"


def test_csv_cadence_rows() -> None:
    cube: dict[str, Any] = {
        "reports": {
            "onboarding": {
                "projects": [
                    {
                        "uuid": "a",
                        "name": "https://github.com/org/a.git",
                        "namespace": "example-tenant",
                    }
                ],
                "cadence": {
                    "weeklyMainFull": [{"w": "2026-01-05", "n": 2}],
                    "weeklyMainWithAnalytics": [{"w": "2026-01-05", "n": 5}],
                    "weeklyCi": [{"w": "2026-01-05", "n": 1}],
                    "byTag": [
                        {
                            "tag": "team-a",
                            "projectCount": 1,
                            "mainFullScans": 2,
                            "ciScans": 1,
                            "mainPerProject": 2.0,
                        }
                    ],
                    "byProject": {"a": {"mainFullScans": 2, "ciScans": 1}},
                },
            }
        }
    }
    weekly = onboarding_cadence_weekly_rows(cube)
    assert weekly[0]["main_full_scans"] == 2
    assert weekly[0]["main_with_analytics"] == 5
    tags = onboarding_cadence_by_tag_rows(cube)
    assert tags[0]["tag"] == "team-a"
    projects = onboarding_cadence_by_project_rows(cube)
    assert projects[0]["uuid"] == "a"


def test_render_onboarding_includes_cadence_controls() -> None:
    cube = {
        "tenant": "example-tenant",
        "pulledAt": "2026-07-29T00:00:00+00:00",
        "tagCatalog": [{"tag": "team-a", "projectCount": 1}],
        "reports": {
            "onboarding": {
                "allRegistrations": 1,
                "distinctRepositories": 1,
                "duplicateRegistrations": 0,
                "weeklyAll": [{"w": "2026-01-05", "n": 1, "c": 1}],
                "weeklyDistinct": [{"w": "2026-01-05", "n": 1, "c": 1}],
                "hierarchyAll": [{"namespace": "example-tenant", "count": 1}],
                "hierarchyDistinct": [{"namespace": "example-tenant", "count": 1}],
                "projects": [
                    {
                        "uuid": "a",
                        "name": "https://github.com/org/a.git",
                        "namespace": "example-tenant",
                        "tags": ["team-a"],
                        "create_time": "2026-01-06T00:00:00Z",
                    }
                ],
                "cadence": {
                    "lookbackDays": 91,
                    "ciLookbackDays": 30,
                    "weeklyMainFull": [{"w": "2026-01-05", "n": 3}],
                    "weeklyMainWithAnalytics": [{"w": "2026-01-05", "n": 4}],
                    "weeklyCi": [{"w": "2026-01-05", "n": 1}],
                    "byProject": {"a": {"mainFullScans": 3, "ciScans": 1}},
                    "byTag": [
                        {
                            "tag": "team-a",
                            "projectCount": 1,
                            "mainFullScans": 3,
                            "ciScans": 1,
                            "mainPerProject": 3.0,
                        }
                    ],
                    "tagProjectUuids": {"team-a": ["a"]},
                    "topProjects": [],
                    "topTags": [],
                    "totals": {
                        "mainFullScans": 3,
                        "ciScans": 1,
                        "distinctPrContextIds": 1,
                    },
                },
            }
        },
    }
    html = _render_onboarding(cube)
    assert "Exclude analytics" in html
    assert "excludeAnalytics" in html
    assert "weeklyMainFull" in html
    assert "Tags by scan cadence" in html
    assert "cadenceScanTotals" in html
    assert "ciLookbackDays" in html
    assert 'id="tag"' in html
    assert "CI / PR scans" in html
    assert "spanGaps" in html
    assert "CI / PR trend" in html


def test_collect_onboarding_cadence_mocked() -> None:
    from endorlabs.workflows.reports.analyze.onboarding_cadence import (
        collect_onboarding_cadence,
    )

    client = MagicMock()
    with (
        patch(
            "endorlabs.workflows.reports.analyze.onboarding_cadence._safe_weekly",
            side_effect=[
                [{"w": "2026-01-05", "n": 2}],
                [{"w": "2026-01-05", "n": 4}],
                [{"w": "2026-01-05", "n": 1}],
            ],
        ),
        patch(
            "endorlabs.workflows.reports.analyze.onboarding_cadence._group_parent_counts",
            side_effect=[
                {"a": 2},  # main full leaf
                {"a": 1},  # ci leaf
            ],
        ),
        patch(
            "endorlabs.workflows.reports.analyze.onboarding_cadence._distinct_context_ids",
            return_value=1,
        ),
    ):
        out = collect_onboarding_cadence(
            client,
            tenant="example-tenant",
            projects=[
                {
                    "uuid": "a",
                    "name": "https://github.com/org/a.git",
                    "namespace": "example-tenant.child",
                    "tags": ["team-a"],
                }
            ],
            leaf_namespaces=["example-tenant.child"],
            tag_catalog=[{"tag": "team-a", "projectCount": 1, "projectUuids": ["a"]}],
        )
    assert out["totals"]["mainFullScans"] == 2
    assert out["totals"]["ciScans"] == 1
    assert out["ciLookbackDays"] == 30
    assert out["topTags"][0]["tag"] == "team-a"
    assert out["weeklyMainFull"][0]["n"] == 2
