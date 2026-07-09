"""Unit tests for operations.pagination."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from endorlabs.operations.pagination import PageCursor, iter_paginated_pages

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


def test_iter_paginated_pages_yields_all_pages() -> None:
    calls: list[PageCursor | None] = []

    def fetch_page(cursor: PageCursor | None) -> dict[str, int]:
        calls.append(cursor)
        if cursor is None:
            return {"page": 1}
        return {"page": 2}

    def next_cursor(page: dict[str, int]) -> PageCursor | None:
        if page["page"] == 1:
            return PageCursor(page_token="tok-2")
        return None

    pages = list(
        iter_paginated_pages(fetch_page, next_cursor=next_cursor, label="test")
    )
    assert pages == [{"page": 1}, {"page": 2}]
    assert calls == [None, PageCursor(page_token="tok-2")]


def test_iter_paginated_pages_page_id_precedence_in_cursor_key() -> None:
    cursor = PageCursor(page_token="ignored", page_id="pid-1")
    assert cursor.cursor_key() == "id:pid-1"


def test_iter_paginated_pages_stops_at_max_pages() -> None:
    def fetch_page(_cursor: PageCursor | None) -> dict[str, str]:
        return {"page": "x"}

    def next_cursor(_page: dict[str, str]) -> PageCursor | None:
        return PageCursor(page_token="always-more")

    pages = list(
        iter_paginated_pages(
            fetch_page,
            next_cursor=next_cursor,
            max_pages=2,
            label="capped",
        )
    )
    assert len(pages) == 2


def test_iter_paginated_pages_stops_on_duplicate_cursor(
    caplog: LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)

    def fetch_page(_cursor: PageCursor | None) -> dict[str, str]:
        return {"page": "x"}

    def next_cursor(_page: dict[str, str]) -> PageCursor | None:
        return PageCursor(page_token="same")

    pages = list(
        iter_paginated_pages(
            fetch_page,
            next_cursor=next_cursor,
            label="dup",
        )
    )
    # First page uses no cursor; duplicate is detected before the third fetch.
    assert len(pages) == 2
    assert "Repeated pagination cursor" in caplog.text


def test_iter_paginated_pages_single_page_when_no_cursor() -> None:
    def fetch_page(_cursor: PageCursor | None) -> str:
        return "only"

    def next_cursor(_page: str) -> PageCursor | None:
        return None

    pages = list(iter_paginated_pages(fetch_page, next_cursor=next_cursor))
    assert pages == ["only"]
