# pyright: reportUninitializedInstanceVariable=false
# ruff: noqa: TC001
"""Private route host mixin for BaseFacade (generated accessor helpers)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from ..core.filter import FilterExpression
from ..operations import BaseResourceOperations
from ..operations.route_contract import RouteContract, RouteEdge
from ..operations.routes import RouteExecutor, RouteResult
from ..registry import RESOURCE_REGISTRY

if TYPE_CHECKING:
    from ..api_client import APIClient


def _registry_attr_by_kind() -> dict[str, str]:
    return {entry.model_class.__name__: entry.attr_name for entry in RESOURCE_REGISTRY}


class RouteHostMixin:
    """Route execution mixin for resource facades (private _execute_route API)."""

    if TYPE_CHECKING:
        _client: APIClient
        _default_namespace: str | None
        _route_contract: RouteContract | None
        _route_executor: RouteExecutor | None

    def _init_route_host(
        self,
        client: APIClient,
        default_namespace: str | None,
        *,
        route_contract: RouteContract | None = None,
    ) -> None:
        self._route_contract = route_contract
        self._route_executor = None
        self._client = client
        self._default_namespace = default_namespace

    def _route_table_for_kind(self, kind: str) -> tuple[RouteEdge, ...]:
        contract = self._route_contract
        if contract is None:
            return ()
        attr = _registry_attr_by_kind().get(kind, kind)
        return contract.edges_for_attr(attr)

    def _route_namespace(self, source: Any, edge: RouteEdge) -> str:
        executor = self._get_route_executor()
        return executor.resolve_namespace(source, edge.namespace_from)

    def _execute_route(
        self,
        edge_id: str,
        *,
        source: Any,
        **list_kwargs: Any,
    ) -> RouteResult[Any]:
        contract = self._route_contract
        if contract is None:
            raise RuntimeError("Route contract not configured on this facade.")
        edge = contract.edge_by_id(edge_id)
        if edge is None:
            raise ValueError(f"Unknown route edge id: {edge_id!r}")
        executor = self._get_route_executor()
        list_fn = None
        entry = getattr(self, "_entry", None)
        if (
            edge.edge == "list_by_parent"
            and entry is not None
            and entry.attr_name == edge.to_kind
            and hasattr(self, "list")
        ):
            list_fn = cast(
                "Callable[..., Any]",
                self.list,  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
            )
        if list_fn is not None:
            executor = RouteExecutor(
                default_namespace=self._default_namespace,
                ops_for_kind=executor.ops_for_kind,
                list_fn_for_parent=list_fn,
            )
        return executor.execute(edge, source=source, **list_kwargs)

    def list_for_context(
        self,
        source: Any,
        *,
        filter: str | FilterExpression | None = None,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> RouteResult[Any]:
        """List rows in the same scan plane as *source*.

        Filters on ``context.type`` and optional ``context.id``.
        """
        entry = getattr(self, "_entry", None)
        if entry is None:
            raise RuntimeError("Route host missing registry entry.")
        contract = self._route_contract
        if contract is None:
            raise RuntimeError("Route contract not configured on this facade.")
        method_name = f"{entry.attr_name}.list_for_context"
        matches = [
            e
            for e in contract.edges
            if e.public_method == method_name and e.edge == "list_by_context_partition"
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"Expected exactly one list_for_context edge for {entry.attr_name!r}, "
                f"found {len(matches)}."
            )
        if filter is not None:
            kwargs = {**kwargs, "filter": filter}
        if namespace is not None:
            kwargs = {**kwargs, "namespace": namespace}
        return self._execute_route(matches[0].id, source=source, **kwargs)

    def _get_route_executor(self) -> RouteExecutor:
        if self._route_executor is not None:
            return self._route_executor
        ops_for_kind: dict[str, BaseResourceOperations[Any]] = {}
        for entry in RESOURCE_REGISTRY:
            kind = entry.model_class.__name__
            ops_for_kind[kind] = BaseResourceOperations(
                self._client, entry.resource_name, entry.model_class
            )
        self._route_executor = RouteExecutor(
            default_namespace=self._default_namespace,
            ops_for_kind=ops_for_kind,
        )
        return self._route_executor
