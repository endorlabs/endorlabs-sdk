"""Serialize list_parameters group knobs for Query POST JSON."""

from __future__ import annotations

from typing import Any

from endorlabs.operations.group_by_time_wire import normalize_group_by_time_interval


def group_query_wire(*aggregation_paths: str) -> dict[str, Any]:
    """Build nested ``list_parameters.group`` for Query POST."""
    paths = [path.strip() for path in aggregation_paths if path.strip()]
    return {"aggregation_paths": ",".join(paths)}


def group_by_time_query_wire(
    *,
    aggregation_paths: str,
    interval: str,
    start_time: str,
    end_time: str,
    mode: str = "count",
    aggregation_operator: str | None = None,
    show_aggregation_uuids: bool | None = None,
) -> dict[str, Any]:
    """Build nested ``list_parameters.group_by_time`` for Query POST."""
    wire: dict[str, Any] = {
        "aggregation_paths": aggregation_paths,
        "interval": normalize_group_by_time_interval(interval),
        "mode": mode,
        "start_time": start_time,
        "end_time": end_time,
    }
    if aggregation_operator is not None:
        wire["aggregation_operator"] = aggregation_operator
    if show_aggregation_uuids is not None:
        wire["show_aggregation_uuids"] = show_aggregation_uuids
    return wire
