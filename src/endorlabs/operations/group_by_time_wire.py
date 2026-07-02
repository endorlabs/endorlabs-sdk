"""Wire serialization for OpenAPI ``list_parameters.group_by_time`` list params."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from endorlabs.core.types import ListParameters

GROUP_BY_TIME_INTERVAL_ALIASES: dict[str, str] = {
    "year": "GROUP_BY_TIME_INTERVAL_YEAR",
    "quarter": "GROUP_BY_TIME_INTERVAL_QUARTER",
    "month": "GROUP_BY_TIME_INTERVAL_MONTH",
    "week": "GROUP_BY_TIME_INTERVAL_WEEK",
    "day": "GROUP_BY_TIME_INTERVAL_DAY",
    "hour": "GROUP_BY_TIME_INTERVAL_HOUR",
    "minute": "GROUP_BY_TIME_INTERVAL_MINUTE",
    "second": "GROUP_BY_TIME_INTERVAL_SECOND",
}


def normalize_group_by_time_interval(interval: str) -> str:
    """Map CLI/SDK aliases (``week``) to OpenAPI enum values."""
    cleaned = interval.strip()
    if cleaned.startswith("GROUP_BY_TIME_INTERVAL_"):
        return cleaned
    wire = GROUP_BY_TIME_INTERVAL_ALIASES.get(cleaned.lower())
    if wire is None:
        allowed = ", ".join(sorted(GROUP_BY_TIME_INTERVAL_ALIASES))
        msg = (
            f"Unsupported group_by_time_interval {interval!r}; "
            f"expected one of: {allowed}"
        )
        raise ValueError(msg)
    return wire


def add_group_by_time_wire_params(
    params: dict[str, Any], list_params: ListParameters
) -> None:
    """Serialize group_by_time knobs to nested list_parameters.group_by_time.*."""
    time_paths = list_params.group_aggregation_paths or []
    if list_params.group_by_time_field_value:
        time_paths = [list_params.group_by_time_field_value, *time_paths]
    if time_paths:
        params["list_parameters.group_by_time.aggregation_paths"] = ",".join(
            dict.fromkeys(time_paths)
        )
    if list_params.group_by_time_interval:
        params["list_parameters.group_by_time.interval"] = (
            normalize_group_by_time_interval(list_params.group_by_time_interval)
        )
    if list_params.group_by_time_mode:
        params["list_parameters.group_by_time.mode"] = list_params.group_by_time_mode
    if list_params.group_by_time_operator:
        params["list_parameters.group_by_time.aggregation_operator"] = (
            list_params.group_by_time_operator
        )
    if list_params.group_show_aggregation_uuids is not None:
        params["list_parameters.group_by_time.show_aggregation_uuids"] = str(
            list_params.group_show_aggregation_uuids
        ).lower()
