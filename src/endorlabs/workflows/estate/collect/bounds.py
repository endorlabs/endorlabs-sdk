"""Shared list pagination bounds: unlimited default (0) and truncation detection."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from endorlabs.utils.logging_config import get_resource_logger

if TYPE_CHECKING:
    from endorlabs.core.types import ListParameters

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


def count_for_progress(
    facade: Any,
    namespace: str,
    *,
    resource_label: str,
    filter_expr: str | None = None,
    traverse: bool = False,
    list_params: ListParameters | None = None,
    logger: logging.Logger | None = None,
) -> int | None:
    """Issue ``facade.count()`` with the same filters as a subsequent list.

    Returns ``None`` on failure (caller should use ``?`` as progress denominator).
    """
    log = logger or _LOGGER
    scope_parts = [f"namespace={namespace}"]
    if traverse:
        scope_parts.append("traverse=true")
    if filter_expr:
        scope_parts.append(f"filter={filter_expr[:80]}")
    scope = " ".join(scope_parts)

    try:
        total = facade.count(
            namespace=namespace,
            filter=filter_expr,
            traverse=traverse,
            list_params=list_params,
        )
    except Exception as exc:
        log.warning(
            "%s count failed (%s); progress denominator unknown",
            resource_label,
            exc,
        )
        return None

    log.info("%s in_scope=%s %s", resource_label, total, scope)
    return int(total)


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
