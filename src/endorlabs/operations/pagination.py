"""Shared cursor pagination loop for list CRUD and Query.create pages.

Internal module — not exported from ``endorlabs.operations`` package surface.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PageCursor:
    """Pagination cursor for one follow-up page request."""

    page_token: str | int | None = None
    page_id: str | None = None

    def cursor_key(self) -> str | None:
        """Stable key for duplicate-cursor detection."""
        if self.page_id is not None:
            return f"id:{self.page_id}"
        if self.page_token is not None:
            return f"token:{self.page_token}"
        return None


_SORT_WIRE_KEYS = (
    "list_parameters.sort.path",
    "list_parameters.sort.order",
)

# Stable tokens for pytest.raises(..., match=) and agent remediation hints.
SORTED_PAGE_ID_REMEDIATION = "max_pages=1"


def list_params_include_sort(params: dict[str, Any]) -> bool:
    """Return True when wire query params include list sort fields."""
    return any(params.get(key) not in (None, "") for key in _SORT_WIRE_KEYS)


def raise_if_page_id_with_sort(params: dict[str, Any]) -> None:
    """Reject follow-up ``page_id`` requests that still carry sort params.

    The platform returns HTTP 400 ("page id cannot be provided with sort
    method"). Raise a clear client-side ``ValidationError`` before that call.
    """
    if not list_params_include_sort(params):
        return
    from endorlabs.core.exceptions import ValidationError

    raise ValidationError(
        "list_parameters.page_id cannot be combined with list_parameters.sort "
        f"(platform rejects sorted page_id cursors). Keep sort with "
        f"{SORTED_PAGE_ID_REMEDIATION} and a larger page_size/limit for N "
        "newest rows, or drop sort_by and paginate then order client-side.",
        operation="list",
    )


def iter_paginated_pages(
    fetch_page: Callable[[PageCursor | None], Any],
    *,
    next_cursor: Callable[[Any], PageCursor | None],
    max_pages: int | None = None,
    label: str = "paginated",
    logger: logging.Logger | None = None,
) -> Iterator[Any]:
    """Yield full page payloads until the cursor chain ends or ``max_pages`` is hit."""
    log = logger or logging.getLogger(__name__)
    page_count = 0
    seen_cursors: set[str] = set()
    cursor: PageCursor | None = None

    while True:
        if max_pages is not None and page_count >= max_pages:
            log.warning(
                "Reached max_pages limit (%s). Stopping pagination after %s pages "
                "for %s.",
                max_pages,
                page_count,
                label,
            )
            break

        cursor_key = cursor.cursor_key() if cursor is not None else None
        if cursor_key is not None:
            if cursor_key in seen_cursors:
                log.warning(
                    "Repeated pagination cursor %s on %s; stopping to avoid loop.",
                    cursor_key,
                    label,
                )
                break
            seen_cursors.add(cursor_key)

        page = fetch_page(cursor)
        yield page
        page_count += 1

        following = next_cursor(page)
        if following is None or following.cursor_key() is None:
            break
        cursor = following

    log.debug("Fetched %s pages for %s", page_count, label)
