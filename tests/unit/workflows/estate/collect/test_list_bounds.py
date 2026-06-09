"""Tests for shared list pagination bounds."""

from __future__ import annotations

from unittest.mock import MagicMock

from endorlabs.workflows.estate.collect.bounds import (
    count_list_delta_check,
    format_progress,
    is_list_truncated,
    list_resource_count,
    list_row_capacity,
    resolve_max_pages,
    truncation_message,
)


def test_resolve_max_pages_unlimited() -> None:
    assert resolve_max_pages(0) is None
    assert resolve_max_pages(-1) is None
    assert resolve_max_pages(None) is None


def test_resolve_max_pages_capped() -> None:
    assert resolve_max_pages(5) == 5


def test_list_row_capacity() -> None:
    assert list_row_capacity(None, 100) is None
    assert list_row_capacity(3, 50) == 150


def test_is_list_truncated_at_capacity() -> None:
    assert is_list_truncated(150, max_pages=3, page_size=50) is True
    assert is_list_truncated(149, max_pages=3, page_size=50) is False
    assert is_list_truncated(999, max_pages=None, page_size=50) is False


def test_truncation_message_unlimited() -> None:
    msg = truncation_message(
        resource="Project",
        scope="ns=tenant",
        row_count=42,
        max_pages=None,
        page_size=100,
    )
    assert "42 rows" in msg
    assert "capacity" not in msg


def test_truncation_message_capped() -> None:
    msg = truncation_message(
        resource="DependencyMetadata",
        scope="project=p1",
        row_count=500,
        max_pages=1,
        page_size=500,
    )
    assert "500" in msg
    assert "max_pages=1" in msg
    assert "0 for unlimited" in msg


def test_format_progress_with_total() -> None:
    assert format_progress("rows", 5, 10) == "rows: 5/10"
    assert format_progress("rows", 5, None) == "rows: 5/?"


def test_count_list_delta_check_match() -> None:
    ok, detail = count_list_delta_check(in_scope_count=100, actual_row_count=100)
    assert ok is True
    assert "matches" in detail


def test_count_list_delta_check_mismatch() -> None:
    ok, detail = count_list_delta_check(in_scope_count=100, actual_row_count=90)
    assert ok is False
    assert "delta=-10" in detail


def test_list_resource_count_success() -> None:
    facade = MagicMock()
    facade._ops.count.return_value = 42
    total = list_resource_count(
        facade,
        "tenant.ns",
        resource_label="Project",
        traverse=True,
    )
    assert total == 42
    facade._ops.count.assert_called_once()


def test_list_resource_count_failure_returns_none() -> None:
    facade = MagicMock()
    facade._ops.count.side_effect = RuntimeError("api down")
    assert (
        list_resource_count(
            facade,
            "tenant.ns",
            resource_label="Project",
        )
        is None
    )
