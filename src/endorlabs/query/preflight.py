"""Unified preflight counts for estate progress denominators."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

from endorlabs.tools.list_bounds import count_for_progress
from endorlabs.utils.logging_config import get_resource_logger

if TYPE_CHECKING:
    from .routing import OutputShape

_LOGGER = get_resource_logger(__name__)

PreflightPlane = Literal["facade", "query"]


def preflight_count(
    client: Any,
    *,
    plane: PreflightPlane,
    namespace: str | None = None,
    projects: list[Any] | None = None,
    shape: OutputShape | None = None,
    resource_label: str = "resource",
    filter_expr: str | None = None,
    traverse: bool = False,
    facade: Any | None = None,
    list_params: Any | None = None,
    logger: logging.Logger | None = None,
) -> int | None:
    """Return a progress denominator via facade ``count()`` or Query recipes."""
    log = logger or _LOGGER
    if plane == "query":
        if not projects or shape is None:
            return None
        try:
            return client.Query.Project.preflight_count(projects, shape)
        except Exception as exc:
            log.warning("Query preflight failed (%s)", exc)
            return None
    if namespace is None or facade is None:
        return None
    return count_for_progress(
        facade,
        namespace,
        resource_label=resource_label,
        filter_expr=filter_expr,
        traverse=traverse,
        list_params=list_params,
        logger=log,
    )
