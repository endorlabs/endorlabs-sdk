"""Typed builders for Query graph join wire payloads."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .filters import project_uuid_in_filter

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

    def connect(self, connect_from: str, connect_to: str) -> Reference:
        """Set parent/child join field names."""
        self._connect_from = connect_from
        self._connect_to = connect_to
        return self

    def count(self, *, filter: str | FilterExpression | None = None) -> Reference:
        """Request a server-side count on the referenced kind."""
        self._list_params["count"] = True
        if filter is not None:
            self._list_params["filter"] = str(filter)
        return self

    def to_wire(self) -> dict[str, Any]:
        """Serialize this reference to Query wire JSON."""
        child: dict[str, Any] = {
            "kind": self._kind,
            "list_parameters": dict(self._list_params),
        }
        if self._return_as:
            child["return_as"] = self._return_as
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
        """Set root ``list_parameters.filter``."""
        self._list_params["filter"] = str(expr)
        return self

    def filter_projects(self, uuids: list[str]) -> QuerySpec:
        """Restrict the root Project list to ``uuids``."""
        filt = project_uuid_in_filter(uuids)
        if filt:
            self._list_params["filter"] = filt
        return self

    def list_parameters(self, **kwargs: Any) -> QuerySpec:
        """Merge extra root ``list_parameters`` keys."""
        self._list_params.update(kwargs)
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

    def for_namespace_batch(self, project_uuids: list[str]) -> dict[str, Any]:
        """Return wire spec scoped to ``project_uuids`` for one leaf namespace POST."""
        wire = self.to_wire()
        lp = dict(wire.get("list_parameters") or {})
        uuid_filter = project_uuid_in_filter(project_uuids)
        if uuid_filter:
            existing = lp.get("filter")
            lp["filter"] = f"{existing} AND {uuid_filter}" if existing else uuid_filter
        wire["list_parameters"] = lp
        return wire
