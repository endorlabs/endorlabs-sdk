"""Unit tests for tag is_in burndown grain (no live API)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from endorlabs.workflows.findings.finding_log_trends import empty_series_cell
from endorlabs.workflows.reports.analyze.burndown_common import (
    PULL_MODE_TAG_IS_IN,
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
                "any",
                "all",
                "reachable",
                "prf",
                "unreachable_function",
            )
        }
        for sev in ("all", "critical", "high", "medium", "low")
    }


def test_sum_severity_reach_matrices() -> None:
    cats = ["2026-01-05", "2026-01-12"]
    a = _matrix(cats, weekly_new=[1, 0], weekly_resolved=[0, 1])
    b = _matrix(cats, weekly_new=[2, 3], weekly_resolved=[1, 0])
    merged = sum_severity_reach_matrices([a, b], categories=cats, period_caption="2w")
    assert merged["critical"]["reachable"]["weeklyNew"] == [3, 3]
    assert merged["critical"]["reachable"]["weeklyResolved"] == [1, 1]
    assert merged["all"]["all"]["weeklyNew"] == [3, 3]


def test_tag_is_in_sums_parent_uuid_sets() -> None:
    cats = ["2026-01-05", "2026-01-12"]
    caption = "2w"
    uid_a = "00000000-0000-4000-8000-00000000000a"
    uid_b = "00000000-0000-4000-8000-00000000000b"
    uid_c = "00000000-0000-4000-8000-00000000000c"
    leaf = "example-tenant.child"
    tenant = "example-tenant"

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

    per_uuid = {
        uid_a: [1, 0],
        uid_b: [2, 0],
        uid_c: [4, 0],
    }

    seed = empty_series_cell(cats, caption)
    is_in_calls: list[tuple[str, tuple[str, ...]]] = []

    def fake_matrix(
        _client: Any,
        *,
        namespace: str,
        parent_uuids: list[str] | None,
        **_kwargs: Any,
    ) -> dict[str, dict[str, dict[str, Any]]]:
        if parent_uuids:
            is_in_calls.append((namespace, tuple(sorted(parent_uuids))))
            assert namespace == tenant
            weekly = [0, 0]
            for uid in parent_uuids:
                part = per_uuid[uid]
                weekly = [weekly[i] + part[i] for i in range(len(weekly))]
            return _matrix(cats, weekly_new=weekly)
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
            tenant=tenant,
            projects=projects,
            leaf_namespaces=[leaf],
            path_options=["all", "example-tenant", leaf],
            tag_catalog=tag_catalog,
            lookback=2,
            min_projects=1,
            max_workers=2,
            include_pr_scope=False,
        )

    policy = report["tagSeriesMeta"]["pullPolicy"]
    assert policy["mode"] == PULL_MODE_TAG_IS_IN
    assert policy["isInPulls"] >= 2
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

    # Tag pulls hit tenant with multi-UUID is_in (not per-project leaf).
    assert any(ns == tenant and len(uids) > 1 for ns, uids in is_in_calls)


def test_pr_active_project_uuids_and_attach_scopes() -> None:
    from endorlabs.workflows.reports.analyze.burndown_common import (
        SCOPE_MAIN,
        SCOPE_PR,
        SERIES_LABELS_PR,
        attach_main_pr_scopes,
        pr_active_project_uuids,
    )

    cadence = {
        "byProject": {
            "00000000-0000-4000-8000-00000000000a": {"ciScans": 2, "mainFullScans": 1},
            "00000000-0000-4000-8000-00000000000b": {"ciScans": 0, "mainFullScans": 3},
        }
    }
    assert pr_active_project_uuids(cadence) == ["00000000-0000-4000-8000-00000000000a"]
    main = {
        "seriesFilters": {"perPath": {}},
        "tagSeries": {"tags": [], "perTag": {}},
        "tagSeriesMeta": {},
        "contextScope": SCOPE_MAIN,
    }
    pr = {
        "seriesFilters": {"perPath": {"all": {}}},
        "tagSeries": {"tags": [], "perTag": {}},
        "tagSeriesMeta": {},
        "contextScope": SCOPE_PR,
        "seriesLabels": SERIES_LABELS_PR,
    }
    out = attach_main_pr_scopes(
        main,
        pr,
        pr_active_uuids=["00000000-0000-4000-8000-00000000000a"],
    )
    assert out["scopes"][SCOPE_MAIN] is main
    assert out["scopes"][SCOPE_PR]["seriesLabels"]["primary"] == "Detected"
    assert out["prActiveProjectUuids"] == ["00000000-0000-4000-8000-00000000000a"]


def test_sca_burndown_includes_pr_scope_when_enabled() -> None:
    cats = ["2026-01-05", "2026-01-12"]
    caption = "2w"
    uid_a = "00000000-0000-4000-8000-00000000000a"
    leaf = "example-tenant.child"
    seed = empty_series_cell(cats, caption)

    def fake_matrix(
        _client: Any,
        *,
        namespace: str,
        parent_uuids: list[str] | None,
        second_series: str = "delete",
        **_kwargs: Any,
    ) -> dict[str, dict[str, dict[str, Any]]]:
        cell = _cell(cats, [1, 0] if second_series == "ci_blocker" else [2, 0], [0, 0])
        return {
            sev: {
                reach: dict(cell)
                for reach in (
                    "any",
                    "all",
                    "reachable",
                    "prf",
                    "unreachable_function",
                )
            }
            for sev in ("all", "critical", "high", "medium", "low")
        }

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
            return_value={uid_a: {"mainScans91d": 0, "ciRunScans21d": 1}},
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
            projects=[
                {
                    "uuid": uid_a,
                    "name": "https://github.com/org/a.git",
                    "namespace": leaf,
                    "tags": ["team-alpha"],
                }
            ],
            leaf_namespaces=[leaf],
            path_options=["all", leaf],
            tag_catalog=[
                {"tag": "team-alpha", "projectCount": 1, "projectUuids": [uid_a]}
            ],
            lookback=2,
            min_projects=1,
            max_workers=2,
            pr_active_uuids=[uid_a],
            include_pr_scope=True,
        )

    assert "scopes" in report
    assert report["scopes"]["pr"]["contextScope"] == "pr"
    assert report["scopes"]["pr"]["seriesLabels"]["primary"] == "Detected"
    assert report["prActiveProjectUuids"] == [uid_a]
    # PR allowlist uses is_in path series.
    assert "all" in report["scopes"]["pr"]["seriesFilters"]["perPath"]
    assert report["scopes"]["pr"]["tagSeriesMeta"]["pullPolicy"]["mode"] == (
        PULL_MODE_TAG_IS_IN
    )


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
