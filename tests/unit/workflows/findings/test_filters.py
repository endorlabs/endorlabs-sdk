"""Unit tests for shared finding list filter fragments."""

from __future__ import annotations

from datetime import UTC, datetime

from endorlabs.filters import (
    finding_log_time_window_filter,
    prd_vuln_filter,
    prf_vuln_filter,
    reachable_vuln_log_base_filter,
)


def test_reachable_vuln_log_base_filter_includes_tags() -> None:
    filt = reachable_vuln_log_base_filter()
    assert "CONTEXT_TYPE_MAIN" in filt
    assert "FINDING_CATEGORY_VULNERABILITY" in filt
    assert "FINDING_TAGS_REACHABLE_FUNCTION" in filt


def test_prf_and_prd_filters_differ_by_tag() -> None:
    prf = prf_vuln_filter()
    prd = prd_vuln_filter()
    assert "POTENTIALLY_REACHABLE_FUNCTION" in prf
    assert "POTENTIALLY_REACHABLE_DEPENDENCY" in prd


def test_finding_log_time_window_filter() -> None:
    start = datetime(2026, 1, 4, tzinfo=UTC)
    end = datetime(2026, 4, 1, tzinfo=UTC)
    filt = finding_log_time_window_filter(
        start,
        end,
        base_filter="spec.operation==OPERATION_CREATE",
    )
    assert "meta.create_time>=date(2026-01-04T00:00:00Z)" in filt
    assert "meta.create_time<date(2026-04-01T00:00:00Z)" in filt
    assert "OPERATION_CREATE" in filt
