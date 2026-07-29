"""Unit tests for project-grain burndown redistribute (no live API)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from endorlabs.workflows.findings.finding_log_trends import empty_series_cell
from endorlabs.workflows.reports.analyze.burndown_common import (
    PULL_MODE_PROJECT_GRAIN,
)
from endorlabs.workflows.reports.analyze.findings_trend import (
    build_findings_burndown_report,
    sum_severity_reach_matrices,
)


def _cell(
    cats: list[str], weekly_new: list[int], weekly_resolved: list[int]
) -> dict[str, Any]:
    cell = empty_series_cell(cats, "2w")
    cell["weeklyNew"] = list(weekly_new)
    cell["weeklyResolved"] = list(weekly_resolved)
    return cell


def _matrix(
    cats: list[str],
    *,
    weekly_new: list[int],
    weekly_resolved: list[int] | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    resolved = weekly_resolved or [0] * len(cats)
    cell = _cell(cats, weekly_new, resolved)
    return {
        sev: {
            reach: dict(cell)
            for reach in (
                "all",
                "reachable",
                "prf",
                "prd",
                "unreachable",
                "unreachable_function",
                "unreachable_dependency",
            )
        }
        for sev in ("all", "critical", "high")
    }


def test_sum_severity_reach_matrices() -> None:
    cats = ["2026-01-05", "2026-01-12"]
    a = _matrix(cats, weekly_new=[1, 0], weekly_resolved=[0, 1])
    b = _matrix(cats, weekly_new=[2, 3], weekly_resolved=[1, 0])
    merged = sum_severity_reach_matrices([a, b], categories=cats, period_caption="2w")
    assert merged["critical"]["reachable"]["weeklyNew"] == [3, 3]
    assert merged["critical"]["reachable"]["weeklyResolved"] == [1, 1]
    assert merged["all"]["all"]["weeklyNew"] == [3, 3]


def test_tag_redistribute_sums_project_matrices() -> None:
    cats = ["2026-01-05", "2026-01-12"]
    caption = "2w"
    uid_a = "00000000-0000-4000-8000-00000000000a"
    uid_b = "00000000-0000-4000-8000-00000000000b"
    uid_c = "00000000-0000-4000-8000-00000000000c"
    leaf = "example-tenant.child"

    projects = [
        {
            "uuid": uid_a,
            "name": "https://github.com/org/a.git",
            "namespace": leaf,
            "tags": ["team-alpha"],
        },
        {
            "uuid": uid_b,
            "name": "https://github.com/org/b.git",
            "namespace": leaf,
            "tags": ["team-alpha", "team-shared"],
        },
        {
            "uuid": uid_c,
            "name": "https://github.com/org/c.git",
            "namespace": leaf,
            "tags": ["team-shared"],
        },
    ]
    tag_catalog = [
        {"tag": "team-alpha", "projectCount": 2, "projectUuids": [uid_a, uid_b]},
        {"tag": "team-shared", "projectCount": 2, "projectUuids": [uid_b, uid_c]},
    ]

    project_matrices = {
        uid_a: _matrix(cats, weekly_new=[1, 0]),
        uid_b: _matrix(cats, weekly_new=[2, 0]),
        uid_c: _matrix(cats, weekly_new=[4, 0]),
    }

    seed = empty_series_cell(cats, caption)

    def fake_matrix(
        _client: Any,
        *,
        namespace: str,
        parent_uuids: list[str] | None,
        **_kwargs: Any,
    ) -> dict[str, dict[str, dict[str, Any]]]:
        if parent_uuids:
            uid = parent_uuids[0]
            return project_matrices[uid]
        # Leaf path aggregate (untagged-inclusive placeholder).
        assert namespace == leaf
        return _matrix(cats, weekly_new=[10, 0])

    with (
        patch(
            "endorlabs.workflows.findings.finding_log_trends."
            "query_severity_facet_series_cell",
            return_value=seed,
        ),
        patch(
            "endorlabs.workflows.findings.finding_log_trends."
            "query_severity_facet_matrix",
            side_effect=fake_matrix,
        ),
        patch(
            "endorlabs.workflows.reports.analyze.findings_trend.collect_scan_throughput",
            return_value={
                uid_a: {"mainScans91d": 0, "ciRunScans21d": 0},
                uid_b: {"mainScans91d": 0, "ciRunScans21d": 0},
                uid_c: {"mainScans91d": 0, "ciRunScans21d": 0},
            },
        ),
        patch(
            "endorlabs.workflows.reports.analyze.findings_trend.probe_scan_history_bounds",
            return_value={
                "lastScanAt": None,
                "oldestScanAt": None,
                "observedRetentionDays": None,
            },
        ),
    ):
        report = build_findings_burndown_report(
            MagicMock(),
            tenant="example-tenant",
            projects=projects,
            leaf_namespaces=[leaf],
            path_options=["all", "example-tenant", leaf],
            tag_catalog=tag_catalog,
            lookback=2,
            min_projects=1,
            max_workers=2,
        )

    policy = report["tagSeriesMeta"]["pullPolicy"]
    assert policy["mode"] == PULL_MODE_PROJECT_GRAIN
    assert policy["taggedProjectsPulled"] == 3
    assert policy["workers"] == 2
    assert set(report["tagSeries"]["tags"]) == {"team-alpha", "team-shared"}

    alpha = report["tagSeries"]["perTag"]["team-alpha"]["all"]["critical"]["reachable"]
    shared = report["tagSeries"]["perTag"]["team-shared"]["all"]["critical"][
        "reachable"
    ]
    # alpha = A+B; shared = B+C (project B counted in both tags).
    assert alpha["weeklyNew"] == [3, 0]
    assert shared["weeklyNew"] == [6, 0]

    # Path series from leaf aggregate, not tagged-only sum.
    path_all = report["seriesFilters"]["perPath"]["all"]["critical"]["reachable"]
    assert path_all["weeklyNew"] == [10, 0]


def test_avg_main_scans_per_project() -> None:
    from endorlabs.workflows.reports.analyze.findings_trend import _throughput_scope

    projects = [
        {
            "uuid": "00000000-0000-4000-8000-000000000001",
            "name": "https://github.com/org/a.git",
            "namespace": "example-tenant.child",
            "tags": [],
        },
        {
            "uuid": "00000000-0000-4000-8000-000000000002",
            "name": "https://github.com/org/b.git",
            "namespace": "example-tenant.child",
            "tags": [],
        },
    ]
    scans = {
        "00000000-0000-4000-8000-000000000001": {
            "mainScans91d": 10,
            "ciRunScans21d": 1,
        },
        "00000000-0000-4000-8000-000000000002": {
            "mainScans91d": 30,
            "ciRunScans21d": 2,
        },
    }
    scope = _throughput_scope(projects, scans)
    assert scope["mainScans91d"] == 40
    assert scope["avgMainScansPerProject"] == 20.0
