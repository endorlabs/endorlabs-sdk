"""Unified preflight counts for estate progress denominators."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

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
    fallback: bool = True,
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
            if fallback and namespace and facade is not None:
                return _facade_preflight(
                    facade,
                    namespace,
                    resource_label=resource_label,
                    filter_expr=filter_expr,
                    traverse=traverse,
                    list_params=list_params,
                    logger=log,
                )
            return None
    if namespace is None or facade is None:
        return None
    return _facade_preflight(
        facade,
        namespace,
        resource_label=resource_label,
        filter_expr=filter_expr,
        traverse=traverse,
        list_params=list_params,
        logger=log,
    )


def _facade_preflight(
    facade: Any,
    namespace: str,
    *,
    resource_label: str,
    filter_expr: str | None,
    traverse: bool,
    list_params: Any | None,
    logger: logging.Logger,
) -> int | None:
    from endorlabs.workflows.estate.collect.bounds import count_for_progress

    return count_for_progress(
        facade,
        namespace,
        resource_label=resource_label,
        filter_expr=filter_expr,
        traverse=traverse,
        list_params=list_params,
        logger=logger,
    )


def query_preflight_count(
    client: Any,
    projects: list[Any],
    shape: OutputShape,
) -> int | None:
    """Return a tenant-wide count total for dashboard-style Query recipes."""
    return preflight_count(
        client,
        plane="query",
        projects=projects,
        shape=shape,
        fallback=False,
    )
