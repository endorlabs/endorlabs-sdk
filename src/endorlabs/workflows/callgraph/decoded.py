"""Shared decoded callgraph payload shaping helpers."""

from __future__ import annotations

from typing import Any

from endorlabs.tools.dependency_explorer import decode_callgraph


def decode_payload(
    cg_data: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Decode raw callgraph payload into summary, callables, and edges."""
    decoded = decode_callgraph(cg_data)
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
