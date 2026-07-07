"""Unit tests for FindingLog new-vs-resolved trend analysis."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from endorlabs.core.exceptions import ServerError
from endorlabs.workflows.findings.finding_log_trends import (
    CHART_DEFAULT_LOOKBACK,
    build_analysis,
    build_finding_log_new_vs_resolved_analysis,
    chart_canvas_filename,
    chart_window_params,
    compute_window,
    cumulative,
    gap_trend,
    normalize_chart_interval,
    query_operation_counts,
    validate_chart_analysis,
)


def test_compute_window_complete_weeks() -> None:
    now = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)
    start, end = compute_window(interval="week", lookback=13, now=now)
    assert start.weekday() == 6
    assert end.weekday() == 6
    assert start < end
    assert (end - start).days == 13 * 7


def test_compute_window_lookback_one_week() -> None:
    now = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)
    start, end = compute_window(interval="week", lookback=1, now=now)
    assert (end - start).days == 7


def test_cumulative_and_gap_trend() -> None:
    assert cumulative([1, 2, 0]) == [1, 3, 3]
    assert gap_trend(1, 3) == "widening"
    assert gap_trend(3, 1) == "narrowing"
    assert gap_trend(2, 2) == "stable"


def test_build_analysis_shape() -> None:
    start = datetime(2026, 1, 4, tzinfo=UTC)
    end = datetime(2026, 1, 18, tzinfo=UTC)
    create = {"2026-01-04T00:00:00Z": 2, "2026-01-11T00:00:00Z": 1}
    delete = {"2026-01-04T00:00:00Z": 1, "2026-01-11T00:00:00Z": 0}
    analysis = build_analysis(
        namespace="tenant",
        window_start=start,
        window_end=end,
        create_counts=create,
        delete_counts=delete,
        severity_split=False,
        interval="week",
        lookback=2,
    )
    assert analysis["namespace"] == "tenant"
    assert analysis["interval"] == "week"
    assert analysis["lookback"] == 2
    assert len(analysis["weeks"]) == 2
    assert analysis["weekly_new"] == [2, 1]
    assert analysis["cumulative_new"] == [2, 3]
    assert analysis["severity_split"] is False


def test_normalize_chart_interval_rejects_non_week_for_chart() -> None:
    try:
        normalize_chart_interval("day")
    except ValueError as exc:
        assert "supports interval" in str(exc)
    else:
        raise AssertionError("expected ValueError for day interval on chart")


def test_build_finding_log_new_vs_resolved_rejects_non_week_interval() -> None:
    class _Client:
        FindingLog = None

    try:
        build_finding_log_new_vs_resolved_analysis(
            _Client(),
            "tenant",
            interval="day",
            lookback=7,
        )
    except ValueError as exc:
        assert "supports interval" in str(exc)
    else:
        raise AssertionError("expected ValueError for non-week interval")


def test_build_analysis_rejects_empty_week_window() -> None:
    start = datetime(2026, 1, 4, tzinfo=UTC)
    end = datetime(2026, 1, 4, tzinfo=UTC)
    try:
        build_analysis(
            namespace="tenant",
            window_start=start,
            window_end=end,
            create_counts={},
            delete_counts={},
            severity_split=False,
        )
    except ValueError as exc:
        assert "no complete weeks" in str(exc)
    else:
        raise AssertionError("expected ValueError for empty week window")


def test_query_operation_counts_severity_split_on_timeout() -> None:
    client = MagicMock()
    calls = {"n": 0}

    def list_groups(**_kwargs: object) -> list[object]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise ServerError("timeout", status_code=504)
        return []

    client.FindingLog.list_groups = list_groups

    counts, split = query_operation_counts(
        client,
        namespace="tenant",
        base_filter="meta.create_time>=date(2026-01-01T00:00:00Z)",
        operation="CREATE",
        traverse=True,
        severity_split=False,
    )
    assert counts == {}
    assert split is True
    assert calls["n"] == 3


def test_query_operation_counts_aggregate_first_on_traverse() -> None:
    client = MagicMock()
    captured: list[bool] = []

    def list_groups(*, traverse: bool = False, **_kwargs: object) -> list[object]:
        captured.append(traverse)
        return []

    client.FindingLog.list_groups = list_groups

    counts, split = query_operation_counts(
        client,
        namespace="tenant",
        base_filter="meta.create_time>=date(2026-01-01T00:00:00Z)",
        operation="CREATE",
        traverse=True,
        severity_split=False,
    )
    assert counts == {}
    assert split is False
    assert captured == [True]


def test_query_operation_counts_falls_back_to_shards_after_aggregate_timeout() -> None:
    from endorlabs.tools.list_sharding import ProjectShard

    client = MagicMock()
    calls = {"aggregate": 0, "shard": 0}

    def list_groups(*, traverse: bool = False, namespace: str = "", **_kwargs: object):
        if traverse:
            calls["aggregate"] += 1
            raise ServerError("timeout", status_code=504)
        calls["shard"] += 1
        return []

    client.FindingLog.list_groups = list_groups
    client.Query.Project.discover.return_value = SimpleNamespace(
        project_shards=lambda: [
            ProjectShard(project_uuid="p-1", namespace="tenant.child", label="child"),
        ]
    )

    counts, split = query_operation_counts(
        client,
        namespace="tenant",
        base_filter="meta.create_time>=date(2026-01-01T00:00:00Z)",
        operation="CREATE",
        traverse=True,
        severity_split=False,
    )
    assert counts == {}
    assert split is True
    assert calls["aggregate"] == 2
    assert calls["shard"] == 2


def test_validate_chart_analysis_accepts_build_analysis_output() -> None:
    start = datetime(2026, 1, 4, tzinfo=UTC)
    end = datetime(2026, 1, 18, tzinfo=UTC)
    analysis = build_analysis(
        namespace="tenant",
        window_start=start,
        window_end=end,
        create_counts={"2026-01-04T00:00:00Z": 1},
        delete_counts={},
        severity_split=False,
        lookback=2,
    )
    validate_chart_analysis(analysis)


def test_chart_window_params_legacy_lookback_days() -> None:
    interval, lookback = chart_window_params({"lookback_days": 14})
    assert interval == "week"
    assert lookback == 2


def test_validate_chart_analysis_rejects_length_mismatch() -> None:
    try:
        validate_chart_analysis(
            {
                "namespace": "tenant",
                "interval": "week",
                "lookback": 2,
                "categories": ["01/04", "01/11"],
                "cumulative_new": [1],
                "cumulative_resolved": [1, 0],
                "finding_criteria": "x",
                "period_caption": "x",
                "gap_start": 0,
                "gap_mid": 0,
                "gap_end": 0,
                "gap_mid_label": "01/04",
                "gap_end_label": "01/11",
                "gap_trend": "stable",
            }
        )
    except ValueError as exc:
        assert "length mismatch" in str(exc)
    else:
        raise AssertionError("expected ValueError for series length mismatch")


def test_chart_canvas_filename_uses_interval_and_lookback() -> None:
    assert (
        chart_canvas_filename("tenant_acme", interval="week", lookback=13)
        == "tenant-acme-cumulative-week-past-13.canvas.tsx"
    )


def test_chart_defaults_match_quarter_window() -> None:
    assert CHART_DEFAULT_LOOKBACK == 13
