"""Tests for list bounds helpers."""

from __future__ import annotations

from unittest.mock import Mock

from endorlabs.workflows.estate.collect.bounds import (
    count_for_progress,
    count_list_delta_check,
    is_list_truncated,
    list_row_capacity,
    resolve_max_pages,
)


def test_resolve_max_pages_unlimited() -> None:
    assert resolve_max_pages(0) is None
    assert resolve_max_pages(None) is None


def test_resolve_max_pages_capped() -> None:
    assert resolve_max_pages(5) == 5


def test_list_row_capacity() -> None:
    assert list_row_capacity(None, 100) is None
    assert list_row_capacity(3, 100) == 300


def test_is_list_truncated_at_capacity() -> None:
    assert is_list_truncated(300, max_pages=3, page_size=100) is True
    assert is_list_truncated(299, max_pages=3, page_size=100) is False


def test_count_list_delta_check_match() -> None:
    ok, detail = count_list_delta_check(in_scope_count=10, actual_row_count=10)
    assert ok is True
    assert "matches" in detail


def test_count_list_delta_check_mismatch() -> None:
    ok, detail = count_list_delta_check(in_scope_count=10, actual_row_count=12)
    assert ok is False
    assert "delta=2" in detail


def test_count_for_progress_success() -> None:
    facade = Mock()
    facade.count = Mock(return_value=42)
    total = count_for_progress(
        facade,
        "tenant.child",
        resource_label="Finding",
        filter_expr='spec.level=="CRITICAL"',
    )
    assert total == 42
    facade.count.assert_called_once()


def test_count_for_progress_failure_returns_none() -> None:
    facade = Mock()
    facade.count = Mock(side_effect=RuntimeError("boom"))
    assert (
        count_for_progress(
            facade,
            "tenant.child",
            resource_label="Finding",
        )
        is None
    )
