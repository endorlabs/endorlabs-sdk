"""Unified PV/finding reachability context builder."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.context.paths import workflow_projects_root
from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.callgraph.decoded import decode_payload
from endorlabs.workflows.list_bounds import is_list_truncated, resolve_max_pages
from endorlabs.workflows.reachability.resolve import (
    ReachabilitySubject,
    resolve_from_finding,
    resolve_from_package_version,
)
from endorlabs.workflows.reachability.stitch import (
    bfs_multi_source,
    build_adjacency,
    build_norm_index,
    find_bridge_norms,
    reconstruct_path,
)


@dataclass
class ReachabilityContextRequest:
    """Input controls for building reachability context."""

    tenant: str
    namespace: str
    output_dir: str = str(workflow_projects_root())
    finding_uuid: str | None = None
    pv_uuid: str | None = None
    decode_zstd: bool = True
    include_oss_callgraph: bool = True
    include_customer_callgraph: bool = True
    max_pages: int = 0
    page_size: int = 200


def _write_json(base: Path, path: Path, payload: Any) -> None:
    safe_write_text(
        base, path, json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    )


def _list_callgraph_for_parent(
    api_client: Any,
    *,
    namespace: str,
    parent_uuid: str | None,
    page_size: int,
    max_pages: int,
) -> tuple[list[dict[str, Any]], bool]:
    if not parent_uuid:
        return [], False
    list_max_pages = resolve_max_pages(max_pages)
    params = {
        "list_parameters.filter": f'meta.parent_uuid=="{parent_uuid}"',
        "list_parameters.page_size": str(page_size),
    }
    objs = list(
        api_client.get_all(
            f"v1/namespaces/{namespace}/call-graph-data",
            params=params,
            max_pages=list_max_pages,
        )
    )
    truncated = is_list_truncated(
        len(objs), max_pages=list_max_pages, page_size=page_size
    )
    return objs, truncated


def _extract_vulnerable_uris(finding: dict[str, Any]) -> list[str]:
    spec = finding.get("spec") or {}
    fmd = spec.get("finding_metadata") or {}
    vuln = fmd.get("vulnerability") or {}
    vspec = vuln.get("spec") or {}
    uris: set[str] = set()
    for affected in vspec.get("affected") or []:
        for u in affected.get("affected_callpath_uris") or []:
            if isinstance(u, str) and u.strip():
                uris.add(u)
    raw = vspec.get("raw") or {}
    endor_v = (raw.get("endor_vulnerability") or {}) if isinstance(raw, dict) else {}
    for comp in endor_v.get("component") or []:
        for u in comp.get("endor_uri") or []:
            if isinstance(u, str) and u.strip() and u != "data-removed":
                uris.add(u)
    return sorted(uris)


def _build_stitching(
    customer_callables: list[dict[str, Any]],
    customer_edges: list[dict[str, Any]],
    oss_callables: list[dict[str, Any]],
    oss_edges: list[dict[str, Any]],
    vulnerable_uris: list[str],
) -> dict[str, Any]:
    customer_index = build_norm_index(customer_callables)
    oss_index = build_norm_index(oss_callables)
    shared = find_bridge_norms(customer_callables, oss_callables)
    customer_bridge_ids = sorted(
        {mid for n in shared for mid in customer_index.get(n, set())}
    )
    oss_bridge_ids = sorted({mid for n in shared for mid in oss_index.get(n, set())})
    vuln_target_ids = sorted(
        {mid for u in vulnerable_uris for mid in oss_index.get(u, set())}
    )

    customer_uri = {r["method_id"]: r.get("uri", "") for r in customer_callables}
    oss_uri = {r["method_id"]: r.get("uri", "") for r in oss_callables}
    customer_starts = [
        mid
        for mid, uri in customer_uri.items()
        if "java://com.indeed:java-spring-service$1.0.0/com.indeed" in uri
    ]

    c_prev = bfs_multi_source(
        customer_starts, build_adjacency(customer_edges), set(customer_bridge_ids)
    )
    customer_bridge_paths: list[dict[str, Any]] = []
    for bid in customer_bridge_ids:
        p = reconstruct_path(c_prev, bid)
        if not p:
            continue
        customer_bridge_paths.append(
            {
                "bridge_id": bid,
                "bridge_uri": customer_uri.get(bid),
                "path_len_edges": len(p) - 1,
                "path_uris": [customer_uri.get(i, "") for i in p],
            }
        )

    o_prev = bfs_multi_source(
        oss_bridge_ids, build_adjacency(oss_edges), set(vuln_target_ids)
    )
    vuln_paths: list[dict[str, Any]] = []
    for tid in vuln_target_ids:
        p = reconstruct_path(o_prev, tid)
        if not p:
            continue
        vuln_paths.append(
            {
                "target_id": tid,
                "target_uri": oss_uri.get(tid),
                "path_len_edges": len(p) - 1,
                "path_uris": [oss_uri.get(i, "") for i in p],
            }
        )
    return {
        "shared_bridge_norms": len(shared),
        "customer_bridge_nodes": len(customer_bridge_ids),
        "customer_reachable_bridge_nodes": len(customer_bridge_paths),
        "oss_bridge_nodes": len(oss_bridge_ids),
        "vulnerable_targets_present_in_oss": len(vuln_target_ids),
        "reachable_vulnerable_targets_from_bridges": len(vuln_paths),
        "sample_customer_bridge_path": customer_bridge_paths[0]
        if customer_bridge_paths
        else None,
        "sample_oss_vulnerable_path": vuln_paths[0] if vuln_paths else None,
    }


def build_reachability_context(request: ReachabilityContextRequest) -> Path:
    """Build and persist normalized reachability context artifact."""
    if not request.finding_uuid and not request.pv_uuid:
        raise ValueError("Provide either finding_uuid or pv_uuid.")
    out_dir = Path(request.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    client = endorlabs.Client(tenant=request.tenant)
    warnings: list[str] = []
    try:
        api_client = getattr(client, "_client", None)
        if api_client is None:
            raise RuntimeError("Client API handle is unavailable.")

        subject: ReachabilitySubject
        finding_obj: dict[str, Any] | None = None
        dep_meta: dict[str, Any] | None = None
        if request.finding_uuid:
            subject, finding_obj, dep_meta = resolve_from_finding(
                api_client,
                namespace=request.namespace,
                finding_uuid=request.finding_uuid,
            )
        else:
            subject, _pv = resolve_from_package_version(
                api_client,
                namespace=request.namespace,
                package_version_uuid=request.pv_uuid or "",
            )

        customer_cg_payload: dict[str, Any] | None = None
        customer_callables: list[dict[str, Any]] = []
        customer_edges: list[dict[str, Any]] = []
        customer_exports: list[dict[str, Any]] = []
        customer_cg_truncated = False
        oss_cg_truncated = False
        if request.include_customer_callgraph and subject.importer_pv_uuid:
            objs, customer_cg_truncated = _list_callgraph_for_parent(
                api_client,
                namespace=request.namespace,
                parent_uuid=subject.importer_pv_uuid,
                page_size=request.page_size,
                max_pages=request.max_pages,
            )
            if customer_cg_truncated:
                warnings.append(
                    "Customer call-graph-data list may be truncated; "
                    "use --max-pages 0 for unlimited."
                )
            if not objs:
                warnings.append(
                    "No customer call-graph-data objects found for importer PV."
                )
            for o in objs:
                cg_uuid = o.get("uuid")
                if not cg_uuid:
                    continue
                full = api_client.get(
                    f"v1/namespaces/{request.namespace}/call-graph-data/{cg_uuid}"
                ).json()
                summary, callables, edges = decode_payload(full)
                customer_exports.append(
                    {
                        "call_graph_uuid": cg_uuid,
                        "summary": summary,
                    }
                )
                customer_callables.extend(callables)
                customer_edges.extend(edges)
            if customer_exports:
                customer_cg_payload = {
                    "exports": customer_exports,
                    "callables_total": len(
                        {r["method_id"] for r in customer_callables}
                    ),
                    "edges_total": len(customer_edges),
                }

        oss_vuln_payload: dict[str, Any] | None = None
        if request.finding_uuid and finding_obj:
            oss_vuln_payload = {
                "extra_key": subject.extra_key,
                "finding_metadata_vulnerability": (
                    ((finding_obj.get("spec") or {}).get("finding_metadata") or {}).get(
                        "vulnerability"
                    )
                ),
            }

        oss_cg_payload: dict[str, Any] | None = None
        oss_callables: list[dict[str, Any]] = []
        oss_edges: list[dict[str, Any]] = []
        if (
            request.include_oss_callgraph
            and subject.oss_namespace
            and subject.oss_package_version_uuid
        ):
            objs, oss_cg_truncated = _list_callgraph_for_parent(
                api_client,
                namespace=subject.oss_namespace,
                parent_uuid=subject.oss_package_version_uuid,
                page_size=request.page_size,
                max_pages=request.max_pages,
            )
            if oss_cg_truncated:
                warnings.append(
                    "OSS call-graph-data list may be truncated; "
                    "use --max-pages 0 for unlimited."
                )
            if not objs:
                warnings.append(
                    "No oss call-graph-data objects found for dependency PV."
                )
            for o in objs:
                cg_uuid = o.get("uuid")
                if not cg_uuid:
                    continue
                full = api_client.get(
                    f"v1/namespaces/{subject.oss_namespace}/call-graph-data/{cg_uuid}"
                ).json()
                summary, callables, edges = decode_payload(full)
                oss_callables.extend(callables)
                oss_edges.extend(edges)
                if not oss_cg_payload:
                    oss_cg_payload = {"exports": []}
                oss_cg_payload["exports"].append(
                    {"call_graph_uuid": cg_uuid, "summary": summary}
                )
            if oss_cg_payload is not None:
                oss_cg_payload["callables_total"] = len(
                    {r["method_id"] for r in oss_callables}
                )
                oss_cg_payload["edges_total"] = len(oss_edges)

        stitching_payload: dict[str, Any] | None = None
        vulnerable_uris: list[str] = []
        if finding_obj:
            vulnerable_uris = _extract_vulnerable_uris(finding_obj)
        if customer_callables and oss_callables:
            stitching_payload = _build_stitching(
                customer_callables,
                customer_edges,
                oss_callables,
                oss_edges,
                vulnerable_uris,
            )

        payload: dict[str, Any] = {
            "generated_at": datetime.now(UTC).isoformat() + "Z",
            "subject": {
                "tenant": request.tenant,
                "namespace": request.namespace,
                "finding_uuid": subject.finding_uuid,
                "project_uuid": subject.project_uuid,
                "importer_pv_uuid": subject.importer_pv_uuid,
                "importer_pv_name": subject.importer_pv_name,
                "target_dependency_uuid": subject.target_dependency_uuid,
                "target_dependency_package_name": (
                    subject.target_dependency_package_name
                ),
                "oss_namespace": subject.oss_namespace,
                "oss_package_version_uuid": subject.oss_package_version_uuid,
                "oss_package_name": subject.oss_package_name,
            },
            "sources": {
                "finding": finding_obj.get("uuid") if finding_obj else None,
                "dependency_metadata": dep_meta.get("uuid") if dep_meta else None,
                "vulnerable_uri_count": len(vulnerable_uris),
            },
            "finding": (
                {
                    "extra_key": (finding_obj.get("spec") or {}).get("extra_key"),
                    "call_graph_analysis_type": (finding_obj.get("spec") or {}).get(
                        "call_graph_analysis_type"
                    ),
                    "reachable_paths_count": len(
                        (finding_obj.get("spec") or {}).get("reachable_paths") or []
                    ),
                    "finding_tags": (finding_obj.get("spec") or {}).get("finding_tags"),
                }
                if finding_obj
                else None
            ),
            "customer_callgraph": customer_cg_payload,
            "oss_vulnerability": oss_vuln_payload,
            "oss_callgraph": oss_cg_payload,
            "stitching": stitching_payload,
            "verdict_hints": {
                "dependency_reachable_hint": (
                    "REACHABLE"
                    in str(
                        (dep_meta or {})
                        .get("spec", {})
                        .get("dependency_data", {})
                        .get("reachable", "")
                    )
                    if dep_meta
                    else None
                ),
                "strict_vulnerable_path_found": (
                    bool(
                        stitching_payload
                        and stitching_payload.get(
                            "reachable_vulnerable_targets_from_bridges", 0
                        )
                        > 0
                    )
                ),
            },
            "list_bounds": {
                "max_pages": request.max_pages,
                "page_size": request.page_size,
                "customer_callgraph_truncated": customer_cg_truncated,
                "oss_callgraph_truncated": oss_cg_truncated,
            },
            "warnings": warnings,
        }
        out_path = out_dir / "reachability_context.json"
        _write_json(out_dir, out_path, payload)
        return out_path
    finally:
        client.close()
