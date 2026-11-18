"""Data-only filter operator / field discovery (SDK-009).

No evaluated Python or executable extensions — inspection only. List vs Query
restrictions are documented; unsupported combinations fail before I/O when
compiled through ``F()`` / Query helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast

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
    field_type: str | None = None
    enum_values: tuple[str, ...] | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class PredicateInspection:
    """Data-only inspection of a predicate input (no I/O / no eval)."""

    schema_version: str
    kind: str
    accepted: bool
    wire_filter: str | None
    errors: tuple[str, ...]
    operators_used: tuple[str, ...]


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
        field_type = "string"
        if path.endswith(("_time", "timestamp")):
            field_type = "datetime"
        elif path.endswith("_uuid") or path == "uuid":
            field_type = "uuid"
        elif "tags" in path or path.endswith("_list"):
            field_type = "array"
        fields.append(
            FilterFieldInfo(
                attr_name=attr_name,
                path=path,
                source=source,
                field_type=field_type,
            )
        )
    return FilterFieldDiscovery(
        schema_version="1",
        attr_name=attr_name,
        fields=tuple(fields),
        enum_snippets_relpath=FILTER_ENUM_SNIPPETS_RELPATH,
    )


def _apply_leaf_predicate(op: str, path: str, value: Any) -> Any:
    """Compile a path/value leaf operator into an ``F`` expression."""
    from endorlabs.core.filter import F

    field = F(path)
    if op in {"eq", "=="}:
        return field == value
    if op in {"ne", "!="}:
        return field != value
    if op in {"gt", ">"}:
        return field > value
    if op in {"ge", ">="}:
        return field >= value
    if op in {"lt", "<"}:
        return field < value
    if op in {"le", "<="}:
        return field <= value
    if op == "matches":
        return field.matches(str(value))
    if op == "contains":
        return field.contains(value)
    raise ValueError(f"unsupported operator: {op}")


def _compile_predicate_node(node: Any, operators: list[str]) -> Any:
    """Compile one structured predicate node into an ``F`` expression."""
    if isinstance(node, str):
        return node
    if not isinstance(node, dict):
        raise TypeError("predicate nodes must be str or dict")
    typed = cast("dict[str, Any]", node)
    op = str(typed.get("op") or "").lower()
    if not op:
        raise ValueError("predicate dict requires 'op'")
    operators.append(op)
    if op in {"and", "or"}:
        args = typed.get("args")
        if not isinstance(args, list) or not args:
            raise ValueError(f"{op} requires non-empty args")
        typed_args = cast("list[Any]", args)
        compiled = [_compile_predicate_node(a, operators) for a in typed_args]
        expr = compiled[0]
        for nxt in compiled[1:]:
            expr = expr & nxt if op == "and" else expr | nxt
        return expr
    if op == "not":
        arg = typed.get("arg")
        if arg is None:
            raise ValueError("not requires 'arg'")
        return ~_compile_predicate_node(arg, operators)
    path = typed.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError(f"{op} requires string 'path'")
    return _apply_leaf_predicate(op, path, typed.get("value"))


def inspect_predicate(
    kind: str,
    predicate: dict[str, Any] | str,
) -> PredicateInspection:
    """Inspect a data-only predicate input against the ``F`` compiler.

    Accepts either a raw filter string or a small structured dict::

        {"op": "eq", "path": "meta.name", "value": "demo"}
        {"op": "and", "args": [...]}

    Never evaluates Python or performs I/O. Unsupported operators fail before
    any network call.
    """
    errors: list[str] = []
    operators: list[str] = []
    wire: str | None = None

    try:
        if isinstance(predicate, str):
            wire = predicate
            operators.append("raw")
        else:
            compiled = _compile_predicate_node(predicate, operators)
            wire = str(compiled)
        accepted = True
    except Exception as exc:
        accepted = False
        errors.append(str(exc))

    return PredicateInspection(
        schema_version="1",
        kind=kind,
        accepted=accepted,
        wire_filter=wire if accepted else None,
        errors=tuple(errors),
        operators_used=tuple(operators),
    )
