"""Typed builders for Query graph join wire payloads."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from endorlabs.filters import project_uuid_in_filter
from endorlabs.filters.query_wire import to_query_filter

from .wire import group_by_time_query_wire, group_query_wire

if TYPE_CHECKING:
    from endorlabs.core.filter import FilterExpression


class Reference:
    """One child reference in a Query graph join."""

    def __init__(self, kind: str, *, return_as: str | None = None) -> None:
        super().__init__()
        self._kind = kind
        self._return_as = return_as
        self._connect_from = "uuid"
        self._connect_to = "spec.project_uuid"
        self._list_params: dict[str, Any] = {}
        self._nested_refs: list[dict[str, Any]] = []

    def connect(self, connect_from: str, connect_to: str) -> Reference:
        """Set parent/child join field names."""
        self._connect_from = connect_from
        self._connect_to = connect_to
        return self

    def count(self, *, filter: str | FilterExpression | None = None) -> Reference:
        """Request a server-side count on the referenced kind."""
        self._list_params["count"] = True
        if filter is not None:
            self._list_params["filter"] = to_query_filter(filter)
        return self

    def list(
        self,
        *,
        filter: str | FilterExpression | None = None,
        mask: str | None = None,
        page_size: int | None = None,
        traverse: bool | None = None,
    ) -> Reference:
        """Request a masked list on the referenced kind (paginate via executor)."""
        if filter is not None:
            self._list_params["filter"] = to_query_filter(filter)
        if mask is not None:
            self._list_params["mask"] = mask
        if page_size is not None:
            self._list_params["page_size"] = page_size
        if traverse is not None:
            self._list_params["traverse"] = traverse
        return self

    def group(self, *aggregation_paths: str) -> Reference:
        """Request grouped aggregation on the referenced kind."""
        self._list_params["group"] = group_query_wire(*aggregation_paths)
        return self

    def group_by_time(
        self,
        *,
        aggregation_paths: str,
        interval: str,
        start_time: str,
        end_time: str,
        mode: str = "count",
    ) -> Reference:
        """Request ``group_by_time`` aggregation on the referenced kind."""
        self._list_params["group_by_time"] = group_by_time_query_wire(
            aggregation_paths=aggregation_paths,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            mode=mode,
        )
        return self

    def reference(self, ref: Reference) -> Reference:
        """Append a nested child reference under this node."""
        self._nested_refs.append(ref.to_wire())
        return self

    def to_wire(self) -> dict[str, Any]:
        """Serialize this reference to Query wire JSON."""
        child: dict[str, Any] = {
            "kind": self._kind,
            "list_parameters": dict(self._list_params),
        }
        if self._return_as:
            child["return_as"] = self._return_as
        if self._nested_refs:
            child["references"] = self._nested_refs
        return {
            "connect_from": self._connect_from,
            "connect_to": self._connect_to,
            "query_spec": child,
        }


class QuerySpec:
    """Root Query graph specification."""

    def __init__(self, root_kind: str) -> None:
        super().__init__()
        self._kind = root_kind
        self._list_params: dict[str, Any] = {"traverse": True}
        self._references: list[dict[str, Any]] = []

    @classmethod
    def root(cls, kind: str) -> QuerySpec:
        """Start a root-kind Query graph specification."""
        return cls(kind)

    def mask(self, mask: str) -> QuerySpec:
        """Set root ``list_parameters.mask``."""
        self._list_params["mask"] = mask
        return self

    def filter(self, expr: str | FilterExpression) -> QuerySpec:
        """Set root ``list_parameters.filter`` (Query wire dialect)."""
        self._list_params["filter"] = to_query_filter(expr)
        return self

    def filter_projects(self, uuids: list[str]) -> QuerySpec:
        """Restrict the root Project list to ``uuids``."""
        filt = project_uuid_in_filter(uuids)
        if filt:
            self._list_params["filter"] = filt
        return self

    def list_parameters(self, **kwargs: Any) -> QuerySpec:
        """Merge extra root ``list_parameters`` keys."""
        if "filter" in kwargs and kwargs["filter"] is not None:
            kwargs = dict(kwargs)
            kwargs["filter"] = to_query_filter(kwargs["filter"])
        self._list_params.update(kwargs)
        return self

    def leaf_scope(self) -> QuerySpec:
        """Set ``traverse=False`` for POST at a project's wire namespace."""
        self._list_params["traverse"] = False
        return self

    def group(self, *aggregation_paths: str) -> QuerySpec:
        """Request grouped aggregation on the root kind."""
        self._list_params["group"] = group_query_wire(*aggregation_paths)
        return self

    def group_by_time(
        self,
        *,
        aggregation_paths: str,
        interval: str,
        start_time: str,
        end_time: str,
        mode: str = "count",
    ) -> QuerySpec:
        """Request ``group_by_time`` on the root kind."""
        self._list_params["group_by_time"] = group_by_time_query_wire(
            aggregation_paths=aggregation_paths,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            mode=mode,
        )
        return self

    def reference(self, ref: Reference) -> QuerySpec:
        """Append a child graph reference."""
        self._references.append(ref.to_wire())
        return self

    def to_wire(self) -> dict[str, Any]:
        """Serialize the full Query graph to wire JSON."""
        spec: dict[str, Any] = {
            "kind": self._kind,
            "list_parameters": dict(self._list_params),
        }
        if self._references:
            spec["references"] = self._references
        return spec

    @property
    def root_kind(self) -> str:
        """Root resource kind for this graph join."""
        return self._kind

    def root_has_uuid_keys(self) -> bool:
        """True when root list rows expose ``uuid`` for scope batching."""
        return self._kind == "Project"

    def for_namespace_batch(self, project_uuids: list[str]) -> dict[str, Any]:
        """Return wire spec scoped to ``project_uuids`` for one leaf namespace POST."""
        return self.for_scope_batch(tuple(project_uuids))

    def for_scope_batch(self, keys: tuple[str, ...]) -> dict[str, Any]:
        """Return wire spec scoped to ``keys`` when root kind supports UUID batching."""
        wire = self.to_wire()
        if not keys or not self.root_has_uuid_keys():
            return wire
        lp = dict(wire.get("list_parameters") or {})
        uuid_filter = project_uuid_in_filter(list(keys))
        if uuid_filter:
            existing = lp.get("filter")
            lp["filter"] = f"{existing} AND {uuid_filter}" if existing else uuid_filter
        wire["list_parameters"] = lp
        return wire

    def with_page_token(self, page_token: int | None) -> dict[str, Any]:
        """Return wire spec with root ``list_parameters.page_token`` set."""
        wire = self.to_wire()
        lp = dict(wire.get("list_parameters") or {})
        if page_token is None:
            lp.pop("page_token", None)
        else:
            lp["page_token"] = page_token
        wire["list_parameters"] = lp
        return wire
