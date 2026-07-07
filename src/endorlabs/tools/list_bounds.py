"""Shared facade list count helpers for progress denominators."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from endorlabs.utils.logging_config import get_resource_logger

if TYPE_CHECKING:
    from endorlabs.core.types import ListParameters

_LOGGER = get_resource_logger(__name__)


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
