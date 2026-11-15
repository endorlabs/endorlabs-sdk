"""Data-only filter operator / field discovery (SDK-009).

No evaluated Python or executable extensions — inspection only. List vs Query
restrictions are documented; unsupported combinations fail before I/O when
compiled through ``F()`` / Query helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FilterPlane = Literal["list", "query", "both"]


@dataclass(frozen=True, slots=True)
class FilterOperatorInfo:
    """One supported filter operator for authoring UIs."""

    name: str
    symbol: str
    planes: FilterPlane
    notes: str = ""


@dataclass(frozen=True, slots=True)
class FilterFieldInfo:
    """One high-leverage filterable field path for a resource kind."""

    attr_name: str
    path: str
    source: Literal["identity_kwarg", "curated", "both"]
    notes: str = ""


@dataclass(frozen=True, slots=True)
class FilterDiscovery:
    """Versioned predicate authoring catalog (no network)."""

    schema_version: str
    operators: tuple[FilterOperatorInfo, ...]
    enum_snippets_relpath: str = "reference/filter-enum-snippets.md"


@dataclass(frozen=True, slots=True)
class FilterFieldDiscovery:
    """Versioned field-path catalog for one resource (no network / no Client)."""

    schema_version: str
    attr_name: str
    fields: tuple[FilterFieldInfo, ...]
    enum_snippets_relpath: str = "reference/filter-enum-snippets.md"


_OPERATORS: tuple[FilterOperatorInfo, ...] = (
    FilterOperatorInfo("eq", "==", "both", "Equality"),
    FilterOperatorInfo("ne", "!=", "both", "Inequality"),
    FilterOperatorInfo("gt", ">", "both"),
    FilterOperatorInfo("ge", ">=", "both"),
    FilterOperatorInfo("lt", "<", "both"),
    FilterOperatorInfo("le", "<=", "both"),
    FilterOperatorInfo(
        "matches",
        "matches",
        "list",
        "Substring/glob-style match on string fields (F().matches)",
    ),
    FilterOperatorInfo(
        "contains",
        "contains",
        "list",
        "Array membership only (F().contains); not for scalar strings",
    ),
    FilterOperatorInfo("and", "and", "both", "Boolean conjunction"),
    FilterOperatorInfo("or", "or", "both", "Boolean disjunction"),
    FilterOperatorInfo("not", "not", "both", "Boolean negation"),
)


def describe_filter_operators() -> FilterDiscovery:
    """Return the documented operator catalog for host authoring surfaces."""
    return FilterDiscovery(schema_version="1", operators=_OPERATORS)


def describe_filter_fields(attr_name: str) -> FilterFieldDiscovery:
    """Return curated + identity filter paths for *attr_name* (no Client).

    Enum value snippets live under ``enum_snippets_relpath`` in agent knowledge
    (wheel or materialized ``.endorlabs/_cache/sdk/``). This is inspection only —
    not a full OpenAPI field schema.
    """
    from endorlabs.facade.description import (
        FILTER_ENUM_SNIPPETS_RELPATH,
        TOP_FILTERABLE_SPEC_PATHS,
        describe_resource,
    )

    desc = describe_resource(attr_name)
    identity_paths = {path for _kw, path in desc.identity_kwargs}
    curated = set(TOP_FILTERABLE_SPEC_PATHS.get(attr_name, ()))
    fields: list[FilterFieldInfo] = []
    for path in desc.filterable_fields:
        in_id = path in identity_paths
        in_cur = path in curated
        if in_id and in_cur:
            source: Literal["identity_kwarg", "curated", "both"] = "both"
        elif in_id:
            source = "identity_kwarg"
        else:
            source = "curated"
        fields.append(FilterFieldInfo(attr_name=attr_name, path=path, source=source))
    return FilterFieldDiscovery(
        schema_version="1",
        attr_name=attr_name,
        fields=tuple(fields),
        enum_snippets_relpath=FILTER_ENUM_SNIPPETS_RELPATH,
    )
