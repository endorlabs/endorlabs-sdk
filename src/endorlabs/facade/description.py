"""Live facade introspection for agents (no network)."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, override


@dataclass(frozen=True)
class ParamInfo:
    """One named parameter from a live method signature."""

    name: str
    type_str: str
    default: str | None


@dataclass(frozen=True)
class FacadeDescription:
    """Compact runtime description of a resource facade."""

    attr_name: str
    resource_name: str
    methods: tuple[str, ...]
    list_params: tuple[ParamInfo, ...]
    identity_kwargs: tuple[tuple[str, str], ...]
    filterable_fields: tuple[str, ...]
    route_methods: tuple[str, ...]
    scope: str | None
    namespace_scoped: bool

    @override
    def __str__(self) -> str:
        """Human-readable map (prefer ``print(facade.describe())`` over repr)."""
        return _format_facade_description(self)


def _annotation_str(annotation: Any) -> str:
    if annotation is inspect.Parameter.empty:
        return "Any"
    if isinstance(annotation, str):
        return annotation
    return getattr(annotation, "__name__", str(annotation).replace("typing.", ""))


def _default_str(default: Any) -> str | None:
    if default is inspect.Parameter.empty:
        return None
    return repr(default)


def list_params_from_signature(method: Any) -> tuple[ParamInfo, ...]:
    """Named parameters of ``list`` (excluding ``self`` and ``**kwargs``)."""
    params: list[ParamInfo] = []
    for name, param in inspect.signature(method).parameters.items():
        if name == "self":
            continue
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            continue
        if param.kind is inspect.Parameter.VAR_POSITIONAL:
            continue
        params.append(
            ParamInfo(
                name=name,
                type_str=_annotation_str(param.annotation),
                default=_default_str(param.default),
            )
        )
    return tuple(params)


def _format_facade_description(d: FacadeDescription) -> str:
    scope_label = d.scope if d.scope is not None else "tenant"
    ns = "yes" if d.namespace_scoped else "no"
    lines = [
        f"{d.attr_name} ({d.resource_name})  scope={scope_label}  "
        f"namespace_scoped={ns}",
    ]
    methods = d.methods
    if len(methods) > 16:
        shown = ", ".join(methods[:16])
        lines.append(f"methods: {shown}, ... (+{len(methods) - 16} more)")
    else:
        lines.append(f"methods: {', '.join(methods)}")

    param_bits: list[str] = []
    for p in d.list_params:
        bit = f"{p.name}: {p.type_str}"
        if p.default is not None:
            bit += f" = {p.default}"
        param_bits.append(bit)
    lines.append(f"list(): {', '.join(param_bits)}")
    if d.identity_kwargs:
        kw = ", ".join(f"{k} -> {v}" for k, v in d.identity_kwargs)
        lines.append(f"identity_kwargs: {kw}")
    else:
        lines.append("identity_kwargs: (none)")
    if d.filterable_fields:
        lines.append(f"filterable: {', '.join(d.filterable_fields)}")
    if d.route_methods:
        lines.append(f"routes: {', '.join(d.route_methods)}")
    return "\n".join(lines)


def build_facade_description(
    *,
    attr_name: str,
    resource_name: str,
    facade_type: type[Any],
    filter_kwarg_map: dict[str, str],
    scope: str | None,
    route_contract: Any,
) -> FacadeDescription:
    """Build a description from live signature + registry + route contract."""
    methods = tuple(
        sorted(
            name
            for name, _obj in inspect.getmembers(
                facade_type, predicate=inspect.isfunction
            )
            if not name.startswith("_")
        )
    )
    list_method = getattr(facade_type, "list", None)
    list_params = (
        list_params_from_signature(list_method) if list_method is not None else ()
    )
    identity_kwargs = tuple(sorted(filter_kwarg_map.items()))
    filterable = tuple(sorted(set(filter_kwarg_map.values())))
    route_methods: list[str] = []
    if route_contract is not None:
        for edge in route_contract.edges_for_attr(attr_name):
            if edge.public_method and "." in edge.public_method:
                route_methods.append(edge.public_method.split(".", 1)[1])
            elif edge.public_method:
                route_methods.append(edge.public_method)
    return FacadeDescription(
        attr_name=attr_name,
        resource_name=resource_name,
        methods=methods,
        list_params=list_params,
        identity_kwargs=identity_kwargs,
        filterable_fields=filterable,
        route_methods=tuple(sorted(set(route_methods))),
        scope=scope,
        namespace_scoped=scope is None,
    )


__all__ = [
    "FacadeDescription",
    "ParamInfo",
    "build_facade_description",
    "list_params_from_signature",
]
