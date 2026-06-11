"""Call graph fetch and decode for PackageVersion-scoped payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..core.exceptions import NotFoundError
from . import validate_namespace
from .list_response import extract_list_objects

if TYPE_CHECKING:
    from ..api_client import APIClient


@dataclass(frozen=True)
class CallGraphDecoded:
    """Unpacked call graph — same contract as sweep/reachability JSON."""

    summary: dict[str, Any]
    callables: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    envelope: dict[str, Any]


def _pv_uuid_and_namespace(
    package_version: Any,
    *,
    namespace: str | None,
) -> tuple[str, str]:
    uuid = getattr(package_version, "uuid", None) or package_version
    if not isinstance(uuid, str) or not uuid:
        raise ValueError("package_version must be a PackageVersion model or UUID str")
    if namespace is not None:
        return uuid, validate_namespace(namespace)
    tenant_meta = getattr(package_version, "tenant_meta", None)
    if tenant_meta is not None:
        ns = getattr(tenant_meta, "namespace", None)
        if ns:
            return uuid, validate_namespace(str(ns))
    raise ValueError(
        "namespace required when package_version is a UUID string without tenant_meta"
    )


def fetch_call_graph_envelope(
    client: APIClient,
    *,
    namespace: str,
    package_version_uuid: str,
) -> dict[str, Any]:
    """List CallGraphData by PV parent UUID and GET full payload."""
    ns = validate_namespace(namespace)
    list_url = f"v1/namespaces/{ns}/call-graph-data"
    params = {
        "list_parameters.filter": f'meta.parent_uuid=="{package_version_uuid}"',
        "list_parameters.page_size": "1",
    }
    resp = client.get(list_url, params=params)
    objects = extract_list_objects(resp.json())
    if not objects:
        raise NotFoundError(
            f"No CallGraphData for PackageVersion {package_version_uuid!r}",
            operation="get_call_graph",
            namespace=ns,
        )

    cg_uuid = objects[0].get("uuid", "")
    if not cg_uuid:
        return objects[0]

    get_url = f"v1/namespaces/{ns}/call-graph-data/{cg_uuid}"
    resp_full = client.get(get_url, headers={"x-callgraph-encoding": "any"})
    return resp_full.json()


def unpack_call_graph_envelope(
    envelope: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Decode a CallGraphData envelope into summary, callables, and edges."""
    from ..workflows.callgraph.proto_decode import decode_callgraph

    decoded = decode_callgraph(envelope)
    callables = [
        {
            "method_id": m.method_id,
            "uri": m.uri,
            "access": m.access,
            "first_line": m.first_line,
            "last_line": m.last_line,
            "defined": m.defined,
        }
        for t in (decoded.internal_types + decoded.external_types)
        for m in t.methods
    ]
    callables = sorted(callables, key=lambda r: r["method_id"])
    edges = [
        {
            "source_id": e.source_id,
            "target_id": e.target_id,
            "source_uri": decoded.callable_label(e.source_id),
            "target_uri": decoded.callable_label(e.target_id),
            "callsite_count": len(e.callsites),
            "call_types": sorted({s.call_type for s in e.callsites}),
        }
        for e in decoded.call_edges
    ]
    summary = {
        "uuid": decoded.uuid,
        "namespace": decoded.namespace,
        "parent_uuid": decoded.parent_uuid,
        "package_name": decoded.package_name,
        "language": decoded.language,
        "version": decoded.version,
        "internal_types": len(decoded.internal_types),
        "external_types": len(decoded.external_types),
        "call_edges": len(decoded.call_edges),
        "total_callables": len(callables),
    }
    return summary, callables, edges


def get_call_graph_for_package_version(
    client: APIClient,
    package_version: Any,
    *,
    namespace: str | None = None,
    decode: bool = True,
) -> CallGraphDecoded | dict[str, Any]:
    """Fetch (and optionally decode) call graph data for a PackageVersion."""
    pv_uuid, ns = _pv_uuid_and_namespace(package_version, namespace=namespace)
    envelope = fetch_call_graph_envelope(
        client, namespace=ns, package_version_uuid=pv_uuid
    )
    if not decode:
        return envelope
    summary, callables, edges = unpack_call_graph_envelope(envelope)
    return CallGraphDecoded(
        summary=summary,
        callables=callables,
        edges=edges,
        envelope=envelope,
    )
