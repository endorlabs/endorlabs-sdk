"""Shared cursor pagination loop for list CRUD and Query.create pages.

Public page/completeness types are exported for host-controlled bounded reads
(SDK-002). Empty or short pages never imply estate-wide absence.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

PageStopReason = Literal[
    "complete",
    "max_pages",
    "max_items",
    "repeated_cursor",
    "deadline",
    "cancelled",
    "error",
]
Completeness = Literal["complete", "capped", "unknown"]


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


@dataclass(frozen=True, slots=True)
class ResourcePage[T]:
    """One bounded list page with owner scope and continuation metadata.

    ``completeness`` is ``complete`` only when the server returned no next
    cursor. A client ``max_pages`` / ``max_items`` cap yields ``capped``.
    When the SDK cannot know whether more rows exist (for example a stop
    before the first page, or host cancellation mid-flight), use ``unknown``.
    An empty ``items`` list with ``completeness != "complete"`` is not proof
    of absence.
    """

    items: tuple[T, ...]
    owner_namespace: str | None  # request scope from the caller; not inferred
    traverse: bool
    requested_page_size: int | None
    page_index: int
    next_cursor: PageCursor | None
    stop_reason: PageStopReason | None
    completeness: Completeness
    pages_fetched: int
    items_fetched: int


@dataclass
class PaginationBound:
    """Client-side budgets and cancel/deadline hooks for pagination."""

    max_pages: int | None = None
    max_items: int | None = None
    should_stop: Callable[[], PageStopReason | None] | None = None
    stop_reason: PageStopReason | None = field(default=None, init=False)
    pages_fetched: int = field(default=0, init=False)
    items_fetched: int = field(default=0, init=False)


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


def completeness_for_stop(
    stop_reason: PageStopReason,
    *,
    had_next_cursor: bool,
) -> Completeness:
    """Map a terminal stop reason to known/unknown/capped completeness."""
    if stop_reason == "complete" and not had_next_cursor:
        return "complete"
    if stop_reason in {"max_pages", "max_items"}:
        return "capped"
    if stop_reason in {"deadline", "cancelled", "error", "repeated_cursor"}:
        return "unknown"
    return "unknown"


def iter_paginated_pages(  # noqa: C901
    fetch_page: Callable[[PageCursor | None], Any],
    *,
    next_cursor: Callable[[Any], PageCursor | None],
    max_pages: int | None = None,
    label: str = "paginated",
    logger: logging.Logger | None = None,
    bound: PaginationBound | None = None,
    extract_items: Callable[[Any], Sequence[Any]] | None = None,
) -> Iterator[Any]:
    """Yield full page payloads until the cursor chain ends or a bound is hit.

    When ``bound`` is provided, records ``stop_reason``, ``pages_fetched``, and
    ``items_fetched`` on that object after iteration ends.
    """
    log = logger or logging.getLogger(__name__)
    control = bound if bound is not None else PaginationBound(max_pages=max_pages)
    inherit_max = (
        bound is not None and max_pages is not None and bound.max_pages is None
    )
    if (bound is None and max_pages is not None) or inherit_max:
        control.max_pages = max_pages

    page_count = 0
    item_count = 0
    seen_cursors: set[str] = set()
    cursor: PageCursor | None = None
    stop: PageStopReason | None = None

    while True:
        if control.should_stop is not None:
            early = control.should_stop()
            if early is not None:
                stop = early
                break
        if control.max_pages is not None and page_count >= control.max_pages:
            stop = "max_pages"
            log.warning(
                "Reached max_pages limit (%s). Stopping pagination after %s pages "
                "for %s.",
                control.max_pages,
                page_count,
                label,
            )
            break
        if control.max_items is not None and item_count >= control.max_items:
            stop = "max_items"
            log.warning(
                "Reached max_items budget (%s). Stopping pagination after %s items "
                "for %s.",
                control.max_items,
                item_count,
                label,
            )
            break

        cursor_key = cursor.cursor_key() if cursor is not None else None
        if cursor_key is not None:
            if cursor_key in seen_cursors:
                stop = "repeated_cursor"
                log.warning(
                    "Repeated pagination cursor %s on %s; stopping to avoid loop.",
                    cursor_key,
                    label,
                )
                break
            seen_cursors.add(cursor_key)

        try:
            page = fetch_page(cursor)
        except Exception:
            stop = "error"
            control.stop_reason = stop
            control.pages_fetched = page_count
            control.items_fetched = item_count
            raise

        yield page
        page_count += 1
        if extract_items is not None:
            batch = extract_items(page)
            item_count += len(batch)
            if control.max_items is not None and item_count >= control.max_items:
                stop = "max_items"
                break

        following = next_cursor(page)
        if following is None or following.cursor_key() is None:
            stop = "complete"
            break
        cursor = following

    # Every ``break`` path assigns ``stop`` before leaving the loop.
    assert stop is not None
    control.stop_reason = stop
    control.pages_fetched = page_count
    control.items_fetched = item_count
    log.debug("Fetched %s pages for %s (stop=%s)", page_count, label, stop)
