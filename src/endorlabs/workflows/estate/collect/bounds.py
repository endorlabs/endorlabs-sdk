"""Shared list pagination bounds: unlimited default (0) and truncation detection."""

from __future__ import annotations

import os

from endorlabs.utils.logging_config import get_resource_logger

_LOGGER = get_resource_logger(__name__)

_COLLECT_MAX_WORKERS_CAP = 16
_COLLECT_MAX_WORKERS_FLOOR = 4


def default_collect_max_workers() -> int:
    """Parallel shard workers from ``os.cpu_count()``, floored at 4 and capped at 16."""
    cpus = os.cpu_count() or _COLLECT_MAX_WORKERS_FLOOR
    return max(_COLLECT_MAX_WORKERS_FLOOR, min(_COLLECT_MAX_WORKERS_CAP, cpus))


def resolve_collect_max_workers(max_workers: int | None) -> int:
    """Use explicit *max_workers* or :func:`default_collect_max_workers`."""
    if max_workers is None:
        return default_collect_max_workers()
    return max(1, max_workers)


def resolve_max_pages(value: int | None) -> int | None:
    """Map CLI max-pages ints to SDK max_pages (None = fetch all pages)."""
    if value is None or value <= 0:
        return None
    return value


def list_row_capacity(max_pages: int | None, page_size: int) -> int | None:
    """Maximum rows fetchable when ``max_pages`` is capped; ``None`` if unlimited."""
    if max_pages is None:
        return None
    return max_pages * page_size


def is_list_truncated(
    row_count: int,
    *,
    max_pages: int | None,
    page_size: int,
) -> bool:
    """True when a capped list likely hit its page budget (row count at capacity)."""
    cap = list_row_capacity(max_pages, page_size)
    return cap is not None and row_count >= cap


def truncation_message(
    *,
    resource: str,
    scope: str,
    row_count: int,
    max_pages: int | None,
    page_size: int,
) -> str:
    """Human-readable truncation detail for logs and phase validation."""
    cap = list_row_capacity(max_pages, page_size)
    if cap is None:
        return f"{resource} {scope}: {row_count} rows"
    return (
        f"{resource} {scope}: listed {row_count} rows "
        f"(capacity {cap} = max_pages={max_pages} * page_size={page_size}); "
        "more may exist — raise cap or use 0 for unlimited"
    )


def format_progress(
    label: str,
    processed: int,
    total: int | None,
    *,
    extra: str = "",
) -> str:
    """Format a progress line with optional known denominator."""
    denom = str(total) if total is not None else "?"
    suffix = f" ({extra})" if extra else ""
    return f"{label}: {processed}/{denom}{suffix}"


from endorlabs.tools.list_bounds import count_for_progress  # noqa: E402

__all__ = [
    "count_for_progress",
    "count_list_delta_check",
    "default_collect_max_workers",
    "format_progress",
    "is_list_truncated",
    "list_row_capacity",
    "resolve_collect_max_workers",
    "resolve_max_pages",
    "truncation_message",
]


def count_list_delta_check(
    *,
    in_scope_count: int | None,
    actual_row_count: int,
) -> tuple[bool, str]:
    """Return phase check (ok, detail) comparing preflight count to listed rows."""
    if in_scope_count is None:
        return True, "preflight count unavailable"
    delta = actual_row_count - in_scope_count
    if delta == 0:
        return True, f"listed {actual_row_count} rows (matches in_scope_count)"
    return (
        False,
        f"listed {actual_row_count} rows vs in_scope_count={in_scope_count} (delta={delta})",
    )
