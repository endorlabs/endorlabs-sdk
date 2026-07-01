# ruff: noqa: D102, D105, UP046, UP047, SIM108
"""Generic route executors for generated relationship accessors."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar, cast

from pydantic import BaseModel

from ..core.exceptions import RouteNotApplicableError
from ..core.filter import F
from ..core.types import ListParameters
from ..facade.context_partition import context_partition_filter
from ..utils.namespace import resolve_namespace_for_resource
from .route_contract import RouteChainStep, RouteEdge, RouteWhen

if TYPE_CHECKING:
    from . import BaseResourceOperations

T = TypeVar("T", bound=BaseModel)


@dataclass
class RouteResult(Generic[T]):
    """Outcome of a stitched route execution.

    List accessors populate ``values``; single-row accessors populate ``value``.
    The result is iterable (``for row in result``) and supports ``len(result)``.
    """

    edge_used: str
    value: T | None = None
    values: list[T] | None = None
    truncated: bool = False
    warnings: list[str] = field(default_factory=list)

    def __iter__(self) -> Iterator[T]:
        if self.values is not None:
            return iter(self.values)
        if self.value is not None:
            return iter([self.value])
        return iter([])

    def __len__(self) -> int:
        if self.values is not None:
            return len(self.values)
        if self.value is not None:
            return 1
        return 0

    def __bool__(self) -> bool:
        return self.value is not None or bool(self.values)

    @property
    def single(self) -> T:
        if self.value is not None:
            return self.value
        if self.values:
            return self.values[0]
        raise RouteNotApplicableError(
            "Route returned no value",
            edge_id=self.edge_used,
        )


def unwrap_route_list(result: RouteResult[T]) -> list[T]:
    """Return list rows from a list-edge ``RouteResult`` (facade public boundary)."""
    if result.values is not None:
        return list(result.values)
    return []


def resolve_attr_path(
    obj: Any, path: str, *, context: dict[str, Any] | None = None
) -> Any:
    """Resolve dotted path; ``source`` / ``through`` prefixes use *context*."""
    if not path:
        return None
    root_key, _, remainder = path.partition(".")
    if context is not None and root_key in context:
        base = context[root_key]
        if not remainder:
            return base
        return resolve_attr_path(base, remainder)
    current = obj
    for part in path.split("."):
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
    return current


def resolve_source_uuid(source: Any) -> str | None:
    """Extract a resource UUID from a model, masked dict row, or raw string."""
    if source is None:
        return None
    if isinstance(source, str):
        cleaned = source.strip()
        return cleaned or None
    value = resolve_attr_path(source, "uuid")
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def format_filter_template(
    template: str, source: Any, context: dict[str, Any] | None = None
) -> str:
    """Replace ``{source...}`` placeholders in filter templates."""

    def repl(match: re.Match[str]) -> str:
        path = match.group(1)
        path = path.removeprefix("source.")
        value = resolve_attr_path(source, path, context=context)
        return "" if value is None else str(value)

    return re.sub(r"\{([^}]+)\}", repl, template)


class RouteExecutor:
    """Execute contract edges against resource operations backends."""

    def __init__(
        self,
        *,
        default_namespace: str | None,
        ops_for_kind: dict[str, BaseResourceOperations[Any]],
        list_fn_for_parent: Any | None = None,
    ) -> None:
        super().__init__()
        self._default_namespace = default_namespace
        self._ops_for_kind = ops_for_kind
        self._list_fn_for_parent = list_fn_for_parent

    def execute(
        self,
        edge: RouteEdge,
        *,
        source: Any,
        filter: str | None = None,
        max_pages: int | None = 1,
        **list_kwargs: Any,
    ) -> RouteResult[Any]:
        self._check_when(edge.when, source, edge.id)
        warnings: list[str] = []
        if edge.list_only:
            warnings.append(
                f"Field {edge.filter_field!r} is list-only (absent on GET schema)."
            )
        ns_override = list_kwargs.pop("namespace", None)
        ns = (
            str(ns_override)
            if ns_override is not None
            else self._resolve_namespace(source, edge.namespace_from)
        )
        if edge.edge == "via_intermediate":
            return self._follow_chain(
                edge, source=source, namespace=ns, filter=filter, **list_kwargs
            )
        if edge.edge == "get_by_uuid":
            return self._get_by_uuid(edge, source=source, namespace=ns)
        if edge.edge == "list_by_parent":
            return self._list_by_parent(
                edge,
                source=source,
                namespace=ns,
                filter=filter,
                max_pages=max_pages,
                **list_kwargs,
            )
        if edge.edge == "list_by_uuid_field":
            return self._list_by_uuid_field(
                edge,
                source=source,
                namespace=ns,
                filter=filter,
                max_pages=max_pages,
                warnings=warnings,
                **list_kwargs,
            )
        if edge.edge == "list_by_index_field":
            return self._list_by_index_field(
                edge,
                source=source,
                namespace=ns,
                filter=filter,
                max_pages=max_pages,
                warnings=warnings,
                **list_kwargs,
            )
        if edge.edge == "list_by_attribute":
            return self._list_by_attribute(
                edge,
                source=source,
                namespace=ns,
                filter=filter,
                max_pages=max_pages,
                **list_kwargs,
            )
        if edge.edge == "list_by_context_partition":
            return self._list_by_context_partition(
                edge,
                source=source,
                namespace=ns,
                filter=filter,
                max_pages=max_pages,
                **list_kwargs,
            )
        raise RouteNotApplicableError(
            f"Unsupported edge kind: {edge.edge}",
            edge_id=edge.id,
        )

    def _ops(self, kind: str) -> BaseResourceOperations[Any]:
        ops = self._ops_for_kind.get(kind)
        if ops is None:
            raise RouteNotApplicableError(
                f"No operations backend for kind {kind!r}",
            )
        return ops

    def _resolve_namespace(self, source: Any, namespace_from: str) -> str:
        if namespace_from == "source":
            ns = resolve_namespace_for_resource(source, self._default_namespace)
        else:
            ns = self._default_namespace
        if not ns:
            raise RouteNotApplicableError("Namespace required for route execution.")
        return ns

    def resolve_namespace(self, source: Any, namespace_from: str) -> str:
        """Public namespace resolver for facade route host."""
        return self._resolve_namespace(source, namespace_from)

    @property
    def ops_for_kind(self) -> dict[str, BaseResourceOperations[Any]]:
        """Operations backends keyed by resource kind name."""
        return self._ops_for_kind

    @staticmethod
    def _check_when(when: RouteWhen | None, source: Any, edge_id: str) -> None:
        if when is None:
            return
        if when.categories:
            cats = resolve_attr_path(source, "spec.finding_categories") or []
            if isinstance(cats, list):
                cat_set = {str(c) for c in cats}
            else:
                cat_set = set()
            if not cat_set.intersection(when.categories):
                raise RouteNotApplicableError(
                    f"Route {edge_id!r} not applicable: finding_categories mismatch.",
                    edge_id=edge_id,
                )
        if when.methods:
            method = resolve_attr_path(source, "spec.method")
            if str(method) not in when.methods:
                raise RouteNotApplicableError(
                    f"Route {edge_id!r} not applicable: spec.method mismatch.",
                    edge_id=edge_id,
                )

    def _get_by_uuid(
        self, edge: RouteEdge, *, source: Any, namespace: str
    ) -> RouteResult[Any]:
        uuid_path = edge.uuid_from or "source.uuid"
        uuid_val = resolve_attr_path(source, uuid_path.replace("source.", "", 1))
        if not uuid_val:
            raise RouteNotApplicableError(
                f"Missing UUID at {uuid_path!r} for route {edge.id!r}.",
                edge_id=edge.id,
            )
        row = self._ops(edge.to_kind).get(namespace, str(uuid_val))
        return RouteResult(edge_used=edge.id, value=row)

    def _list_by_parent(
        self,
        edge: RouteEdge,
        *,
        source: Any,
        namespace: str,
        filter: str | None,
        max_pages: int | None,
        **list_kwargs: Any,
    ) -> RouteResult[Any]:
        if self._list_fn_for_parent is not None:
            rows = self._list_fn_for_parent(
                parent=source,
                namespace=namespace,
                filter=filter,
                max_pages=max_pages,
                **list_kwargs,
            )
            return RouteResult(
                edge_used=edge.id,
                values=list(rows),
                truncated=max_pages is not None
                and len(rows) >= (list_kwargs.get("page_size") or 0),
            )
        parent_uuid = resolve_source_uuid(source)
        if not parent_uuid:
            raise RouteNotApplicableError(
                "Missing parent UUID on source resource.",
                edge_id=edge.id,
            )
        clause = str(F("meta.parent_uuid") == parent_uuid)
        merged = f"{filter} AND {clause}" if filter else clause
        lp = ListParameters(filter=merged) if merged else None  # pyright: ignore[reportCallIssue]
        rows = self._ops(edge.to_kind).list(namespace, lp, max_pages)
        return RouteResult(edge_used=edge.id, values=list(rows))

    def _list_by_uuid_field(
        self,
        edge: RouteEdge,
        *,
        source: Any,
        namespace: str,
        filter: str | None,
        max_pages: int | None,
        warnings: list[str],
        **list_kwargs: Any,
    ) -> RouteResult[Any]:
        _ = list_kwargs
        uuid_path = edge.uuid_from or "source.uuid"
        uuid_val = resolve_attr_path(
            source,
            uuid_path.replace("source.", "", 1)
            if uuid_path.startswith("source.")
            else uuid_path,
        )
        if not uuid_val:
            raise RouteNotApplicableError(
                f"Missing UUID for filter at {uuid_path!r}.",
                edge_id=edge.id,
            )
        field = edge.filter_field or "spec.project_uuid"
        clause = f'{field}=="{uuid_val}"'
        filter_text = str(filter) if filter is not None else None
        merged = f"{filter_text} AND {clause}" if filter_text else clause
        lp = ListParameters(filter=merged)  # pyright: ignore[reportCallIssue]
        rows = self._ops(edge.to_kind).list(namespace, lp, max_pages, **list_kwargs)
        return RouteResult(
            edge_used=edge.id, values=list(rows), warnings=list(warnings)
        )

    def _list_by_index_field(
        self,
        edge: RouteEdge,
        *,
        source: Any,
        namespace: str,
        filter: str | None,
        max_pages: int | None,
        warnings: list[str],
        **list_kwargs: Any,
    ) -> RouteResult[Any]:
        return self._list_by_uuid_field(
            edge,
            source=source,
            namespace=namespace,
            filter=filter,
            max_pages=max_pages,
            warnings=warnings,
            **list_kwargs,
        )

    def _list_by_context_partition(
        self,
        edge: RouteEdge,
        *,
        source: Any,
        namespace: str,
        filter: str | None,
        max_pages: int | None,
        **list_kwargs: Any,
    ) -> RouteResult[Any]:
        context_path = edge.context_from or "context"
        context = resolve_attr_path(source, context_path)
        if context is None or not getattr(context, "type", None):
            raise RouteNotApplicableError(
                f"Missing context partition at {context_path!r} on source.",
                edge_id=edge.id,
            )
        clause = context_partition_filter(context)
        if edge.also_filter:
            extra = format_filter_template(edge.also_filter, source)
            clause = f"{extra} AND {clause}"
        filter_text = str(filter) if filter is not None else None
        merged = f"{filter_text} AND {clause}" if filter_text else clause
        lp = ListParameters(filter=merged)  # pyright: ignore[reportCallIssue]
        rows = self._ops(edge.to_kind).list(namespace, lp, max_pages, **list_kwargs)
        return RouteResult(edge_used=edge.id, values=list(rows))

    def _list_by_attribute(
        self,
        edge: RouteEdge,
        *,
        source: Any,
        namespace: str,
        filter: str | None,
        max_pages: int | None,
        **list_kwargs: Any,
    ) -> RouteResult[Any]:
        attr = edge.source_attr
        if not attr or not edge.target_filter_field:
            raise RouteNotApplicableError(
                "list_by_attribute requires source_attr and target_filter_field.",
                edge_id=edge.id,
            )
        value = resolve_attr_path(source, attr)
        if not value:
            raise RouteNotApplicableError(
                f"Missing attribute {attr!r} on source.",
                edge_id=edge.id,
            )
        match_mode: Literal["exact", "substring", "regex"] = edge.match or "exact"
        text = str(value)
        if match_mode == "exact":
            clause = f'{edge.target_filter_field}=="{text}"'
        elif match_mode == "substring":
            clause = f'{edge.target_filter_field} matches "{text}"'
        else:
            clause = f'{edge.target_filter_field} matches "{text}"'
        if edge.also_filter:
            extra = format_filter_template(edge.also_filter, source)
            clause = f"{extra} AND {clause}"
        filter_text = str(filter) if filter is not None else None
        merged = f"{filter_text} AND {clause}" if filter_text else clause
        lp = ListParameters(filter=merged)  # pyright: ignore[reportCallIssue]
        rows = self._ops(edge.to_kind).list(namespace, lp, max_pages, **list_kwargs)
        truncated = len(rows) > 1
        warnings: list[str] = []
        if truncated:
            warnings.append(
                f"Attribute route {edge.id!r} returned {len(rows)} rows; using first."
            )
        return RouteResult(
            edge_used=edge.id,
            value=cast("Any", rows[0]) if rows else None,
            values=list(rows),
            truncated=truncated,
            warnings=warnings,
        )

    def _follow_chain(
        self,
        edge: RouteEdge,
        *,
        source: Any,
        namespace: str,
        filter: str | None,
        **list_kwargs: Any,
    ) -> RouteResult[Any]:
        context: dict[str, Any] = {"source": source}
        last_error: Exception | None = None
        for step in edge.steps:
            try:
                result = self._execute_step(
                    step,
                    edge=edge,
                    source=source,
                    context=context,
                    namespace=namespace,
                    filter=filter,
                    **list_kwargs,
                )
                if result.value is not None:
                    return RouteResult(
                        edge_used=edge.id,
                        value=result.value,
                        warnings=result.warnings,
                    )
                if result.values and step.kind != "get_by_uuid":
                    context["through"] = result.values[0]
                    continue
            except RouteNotApplicableError as err:
                last_error = err
                if step.optional:
                    continue
                raise
        if last_error is not None:
            raise last_error
        raise RouteNotApplicableError(
            f"Chain route {edge.id!r} exhausted without a result.",
            edge_id=edge.id,
        )

    def _execute_step(
        self,
        step: RouteChainStep,
        *,
        edge: RouteEdge,
        source: Any,
        context: dict[str, Any],
        namespace: str,
        filter: str | None,
        **list_kwargs: Any,
    ) -> RouteResult[Any]:
        if step.kind == "list_by_uuid_field":
            through_kind = step.through_kind or edge.to_kind
            uuid_path = step.uuid_from or "source.spec.project_uuid"
            uuid_val = resolve_attr_path(
                source, uuid_path.replace("source.", "", 1), context=context
            )
            if not uuid_val:
                raise RouteNotApplicableError(
                    f"Missing uuid for chain step at {uuid_path!r}.",
                    edge_id=edge.id,
                )
            field = step.filter_field or "spec.project_uuid"
            clause = f'{field}=="{uuid_val}"'
            lp = ListParameters(filter=clause)  # pyright: ignore[reportCallIssue]
            rows = self._ops(through_kind).list(
                namespace, lp, list_kwargs.get("max_pages", 1)
            )
            if not rows:
                raise RouteNotApplicableError(
                    f"No {through_kind} rows for chain step.",
                    edge_id=edge.id,
                )
            context["through"] = rows[0]
            return RouteResult(edge_used=edge.id, values=list(rows))
        if step.kind == "get_by_uuid":
            through = context.get("through", source)
            uuid_path = (step.uuid_from or "through.spec.semgrep.rule_uuid").replace(
                "through.", "", 1
            )
            uuid_val = resolve_attr_path(through, uuid_path, context=context)
            if not uuid_val:
                raise RouteNotApplicableError(
                    f"Missing uuid at {step.uuid_from!r}.",
                    edge_id=edge.id,
                )
            row = self._ops(edge.to_kind).get(namespace, str(uuid_val))
            return RouteResult(edge_used=edge.id, value=row)
        if step.kind == "list_by_attribute":
            through = context.get("through", source)
            attr_path = (step.source_attr or "").replace("through.", "", 1)
            pseudo = through
            value = resolve_attr_path(pseudo, attr_path, context=context)
            if not value:
                raise RouteNotApplicableError(
                    f"Missing chain attribute {step.source_attr!r}.",
                    edge_id=edge.id,
                )
            sub_edge = RouteEdge(
                id=edge.id,
                from_kind=edge.from_kind,
                to_kind=edge.to_kind,
                edge="list_by_attribute",
                source_attr=attr_path,
                target_filter_field=step.target_filter_field,
                match=step.match or "substring",
            )
            # Reuse list_by_attribute with through as source
            return self._list_by_attribute(
                sub_edge,
                source=through,
                namespace=namespace,
                filter=filter,
                max_pages=list_kwargs.get("max_pages", 1),
            )
        raise RouteNotApplicableError(
            f"Unsupported chain step kind: {step.kind}",
            edge_id=edge.id,
        )
