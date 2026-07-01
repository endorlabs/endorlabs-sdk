"""Unit tests for FindingLog new-vs-resolved trend analysis."""

from __future__ import annotations

from datetime import UTC, datetime

from endorlabs.workflows.findings.finding_log_trends import (
    build_analysis,
    build_finding_log_new_vs_resolved_analysis,
    compute_window,
    cumulative,
    gap_trend,
)


def test_compute_window_complete_weeks() -> None:
    now = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)
    start, end = compute_window(now=now, lookback_days=90)
    assert start.weekday() == 6
    assert end.weekday() == 6
    assert start < end


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
    )
    assert analysis["namespace"] == "tenant"
    assert len(analysis["weeks"]) == 2
    assert analysis["weekly_new"] == [2, 1]
    assert analysis["cumulative_new"] == [2, 3]
    assert analysis["severity_split"] is False


def test_build_finding_log_new_vs_resolved_rejects_non_week_interval() -> None:
    class _Client:
        FindingLog = None

    try:
        build_finding_log_new_vs_resolved_analysis(
            _Client(),
            "tenant",
            interval="day",
        )
    except ValueError as exc:
        assert "interval='week'" in str(exc)
    else:
        raise AssertionError("expected ValueError for non-week interval")
