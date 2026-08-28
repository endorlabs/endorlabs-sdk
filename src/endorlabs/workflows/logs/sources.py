"""Shared PackageFirewallLog / AgentHookEvent list and count adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast

from endorlabs.operations.list_response import count_from_wire
from endorlabs.workflows.wire_access import as_dict

if TYPE_CHECKING:
    from endorlabs.client_surface import Client

# CLI / workflow tokens (product ontology). Wire paths stay internal.
LogSource = Literal["package-firewall-logs", "policy-violations"]

_AGENT_HOOK_EVENTS_PATH = "agent-hook-events"

SOURCE_RESOURCE: dict[LogSource, str] = {
    "package-firewall-logs": "package-firewall-logs",
    "policy-violations": _AGENT_HOOK_EVENTS_PATH,
}


def row_to_dict(row: Any) -> dict[str, Any]:
    """Serialize a facade model or dict row to a plain JSON-compatible dict."""
    if isinstance(row, dict):
        return cast("dict[str, Any]", row)
    dump = getattr(row, "model_dump", None)
    if callable(dump):
        data = dump(mode="json", exclude_none=False)
        if isinstance(data, dict):
            return cast("dict[str, Any]", data)
    raise TypeError(f"Unsupported log row type: {type(row)!r}")


def _api_transport(client: Client) -> Any:
    api = client._client  # noqa: SLF001 — AgentHookEvent has no facade yet
    if api is None:
        raise RuntimeError("Client has no API transport (closed?)")
    return api


def count_package_firewall(
    client: Client,
    *,
    namespace: str,
    filter_expr: str | None,
) -> int:
    """Count PackageFirewallLog rows in one namespace (no traverse)."""
    kwargs: dict[str, Any] = {"namespace": namespace, "traverse": False}
    if filter_expr:
        kwargs["filter"] = filter_expr
    return int(client.PackageFirewallLog.count(**kwargs))


def count_agent_hook_events(
    client: Client,
    *,
    namespace: str,
    filter_expr: str | None,
) -> int:
    """Count AgentHookEvent rows via raw list count (x-internal; no facade)."""
    api = _api_transport(client)
    url = f"v1/namespaces/{namespace}/{_AGENT_HOOK_EVENTS_PATH}"
    params: dict[str, Any] = {"list_parameters.count": "true"}
    if filter_expr:
        params["list_parameters.filter"] = filter_expr
    res = api.get(url, params=params)
    data = as_dict(res.json() if hasattr(res, "json") else res)
    return count_from_wire(data)


def count_log_events(
    client: Client,
    source: LogSource,
    *,
    namespace: str,
    filter_expr: str | None = None,
) -> int:
    """Count log events for ``source`` in one namespace (no traverse)."""
    if source == "package-firewall-logs":
        return count_package_firewall(
            client, namespace=namespace, filter_expr=filter_expr
        )
    if source == "policy-violations":
        return count_agent_hook_events(
            client, namespace=namespace, filter_expr=filter_expr
        )
    raise ValueError(f"Unknown source: {source!r}")


def list_package_firewall(
    client: Client,
    *,
    namespace: str,
    filter_expr: str | None,
    traverse: bool = False,
) -> list[dict[str, Any]]:
    """List PackageFirewallLog rows as dicts."""
    kwargs: dict[str, Any] = {"namespace": namespace, "traverse": traverse}
    if filter_expr:
        kwargs["filter"] = filter_expr
    rows = client.PackageFirewallLog.list(**kwargs)
    return [row_to_dict(row) for row in rows]


def list_agent_hook_events(
    client: Client,
    *,
    namespace: str,
    filter_expr: str | None,
    traverse: bool = False,
) -> list[dict[str, Any]]:
    """List AgentHookEvent rows via raw get_all (x-internal; no facade)."""
    api = _api_transport(client)
    url = f"v1/namespaces/{namespace}/{_AGENT_HOOK_EVENTS_PATH}"
    params: dict[str, Any] = {}
    if traverse:
        params["list_parameters.traverse"] = "true"
    if filter_expr:
        params["list_parameters.filter"] = filter_expr
    return [row_to_dict(row) for row in api.get_all(url, params=params)]


def list_log_events(
    client: Client,
    source: LogSource,
    *,
    namespace: str,
    filter_expr: str | None = None,
    traverse: bool = False,
) -> list[dict[str, Any]]:
    """List full log rows for ``source``."""
    if source == "package-firewall-logs":
        return list_package_firewall(
            client,
            namespace=namespace,
            filter_expr=filter_expr,
            traverse=traverse,
        )
    if source == "policy-violations":
        return list_agent_hook_events(
            client,
            namespace=namespace,
            filter_expr=filter_expr,
            traverse=traverse,
        )
    raise ValueError(f"Unknown source: {source!r}")


__all__ = [
    "SOURCE_RESOURCE",
    "LogSource",
    "count_agent_hook_events",
    "count_log_events",
    "count_package_firewall",
    "list_agent_hook_events",
    "list_log_events",
    "list_package_firewall",
    "row_to_dict",
]
