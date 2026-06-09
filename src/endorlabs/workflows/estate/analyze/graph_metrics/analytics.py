"""Local graph analytics on enriched compile-dependency graph artifacts."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from endorlabs.tools.dependency_explorer import write_json
from endorlabs.workflows.estate.collect.dependency_metadata import (
    dep_data_from_record,
    load_dependency_metadata_records,
)
from endorlabs.workflows.estate.workspace.paths import ir_path

GRAPH_METRICS_SCHEMA = "endor.graph_metrics.v1"
PACKAGE_SUBGRAPH_SCHEMA = "endor.package_subgraph.v1"


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def _load_graph(workspace_root: Path) -> dict[str, Any]:
    for name in (
        "compile_dependency_graph_enriched.json",
        "compile_dependency_graph.json",
    ):
        path = ir_path(workspace_root, name)
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    msg = f"No compile graph under {workspace_root / 'intermediate-representation'}"
    raise FileNotFoundError(msg)


def _build_igraph(graph: dict[str, Any]) -> Any:
    import igraph as ig  # pyright: ignore[reportMissingTypeStubs]

    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    g = ig.Graph(directed=True)
    g.add_vertices(len(nodes))
    id_to_idx = {int(n["node_id"]): i for i, n in enumerate(nodes) if "node_id" in n}
    e_pairs = []
    weights = []
    for edge in edges:
        importer_id = int(edge["importer_vertex_id"])
        producer_id = int(edge["producer_vertex_id"])
        if importer_id in id_to_idx and producer_id in id_to_idx:
            e_pairs.append((id_to_idx[importer_id], id_to_idx[producer_id]))
            weights.append(float(edge.get("import_evidence_count") or 1))
    if e_pairs:
        g.add_edges(e_pairs)
        g.es["weight"] = weights
    g.vs["node_id"] = [int(n["node_id"]) for n in nodes]
    g.vs["name"] = [str(n.get("name") or "") for n in nodes]
    return g, id_to_idx


def compute_graph_metrics(
    graph: dict[str, Any],
    *,
    max_betweenness_nodes: int = 5000,
) -> dict[str, Any]:
    g, _id_to_idx = _build_igraph(graph)
    nodes = graph.get("nodes") or []
    n = g.vcount()

    wcc = g.components(mode="weak")
    scc = g.components(mode="strong")

    in_deg = g.indegree()
    out_deg = g.outdegree()
    idx_to_node_id = {i: int(nodes[i]["node_id"]) for i in range(len(nodes))}

    centrality: dict[str, Any] = {
        "in_degree_top": sorted(
            [{"node_id": idx_to_node_id[i], "value": int(in_deg[i])} for i in range(n)],
            key=lambda x: (-x["value"], x["node_id"]),
        )[:50],
        "out_degree_top": sorted(
            [
                {"node_id": idx_to_node_id[i], "value": int(out_deg[i])}
                for i in range(n)
            ],
            key=lambda x: (-x["value"], x["node_id"]),
        )[:50],
    }

    if n > 0 and n <= max_betweenness_nodes:
        pr = g.pagerank(directed=True, weights="weight")
        centrality["pagerank_top"] = sorted(
            [{"node_id": idx_to_node_id[i], "value": float(pr[i])} for i in range(n)],
            key=lambda x: (-x["value"], x["node_id"]),
        )[:50]
        bt = g.betweenness(directed=True, weights="weight")
        centrality["betweenness_top"] = sorted(
            [{"node_id": idx_to_node_id[i], "value": float(bt[i])} for i in range(n)],
            key=lambda x: (-x["value"], x["node_id"]),
        )[:50]
    else:
        centrality["pagerank_skipped"] = f"n={n} exceeds max_betweenness_nodes"
        centrality["betweenness_skipped"] = f"n={n} exceeds max_betweenness_nodes"

    k_core: dict[str, Any] = {}
    if n > 0:
        ug = g.as_undirected(combine_edges="sum")
        coreness = ug.coreness()
        if coreness:
            max_core = max(coreness)
            k_core = {
                "max_k": int(max_core),
                "nodes_at_max_k": [
                    idx_to_node_id[i] for i, k in enumerate(coreness) if k == max_core
                ][:100],
            }

    components = {
        "weakly_connected_count": len(wcc),
        "weakly_connected_sizes": sorted([len(c) for c in wcc], reverse=True)[:20],
        "strongly_connected_count": len(scc),
        "strongly_connected_sizes": sorted([len(c) for c in scc], reverse=True)[:20],
    }

    scc_info: dict[str, Any] = {"cyclic_components": []}
    for comp in scc:
        if len(comp) > 1:
            scc_info["cyclic_components"].append(
                {
                    "size": len(comp),
                    "node_ids": [idx_to_node_id[i] for i in comp[:25]],
                }
            )
    scc_info["has_cycles"] = len(scc_info["cyclic_components"]) > 0

    return {
        "schema": GRAPH_METRICS_SCHEMA,
        "namespace": graph.get("namespace"),
        "generated_at": _utc_now(),
        "node_count": n,
        "edge_count": g.ecount(),
        "centrality": centrality,
        "components": components,
        "scc": scc_info,
        "k_core": k_core,
    }


def build_package_subgraph(
    corpus_records: list[dict[str, Any]],
    *,
    package_name_match: str,
    graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Induced project set and corpus stats for one package coordinate."""
    needle = package_name_match.strip().lower()
    consumer_uuids: set[str] = set()
    version_counts: dict[str, int] = defaultdict(int)
    direct_count = 0
    oss_count = 0
    for rec in corpus_records:
        dep = dep_data_from_record(rec)
        pkg = str(dep.get("package_name") or "")
        if needle not in pkg.lower():
            continue
        uid = str(rec.get("project_uuid") or "")
        if uid:
            consumer_uuids.add(uid)
        ver = str(dep.get("resolved_version") or dep.get("unresolved_version") or "")
        if ver:
            version_counts[ver] += 1
        if dep.get("direct"):
            direct_count += 1
        if str(dep.get("namespace") or "") == "oss":
            oss_count += 1

    induced_nodes: list[dict[str, Any]] = []
    if graph:
        for node in graph.get("nodes") or []:
            uuids = set(node.get("project_uuids") or [])
            if node.get("project_uuid"):
                uuids.add(str(node["project_uuid"]))
            if consumer_uuids & {str(u) for u in uuids}:
                induced_nodes.append(
                    {
                        "node_id": node.get("node_id"),
                        "name": node.get("name"),
                        "project_uuids": sorted(uuids),
                    }
                )

    return {
        "schema": PACKAGE_SUBGRAPH_SCHEMA,
        "package_name_match": package_name_match,
        "generated_at": _utc_now(),
        "consumer_project_count": len(consumer_uuids),
        "corpus_row_count": sum(version_counts.values()),
        "direct_row_count": direct_count,
        "oss_row_count": oss_count,
        "resolved_version_counts": dict(sorted(version_counts.items())),
        "consumer_project_uuids_sample": sorted(consumer_uuids)[:100],
        "induced_graph_nodes": induced_nodes[:200],
    }


def run_graph_analytics_phase(
    workspace_root: Path,
    *,
    package_name_match: str | None = None,
    max_betweenness_nodes: int = 5000,
) -> dict[str, Any]:
    graph = _load_graph(workspace_root)
    metrics = compute_graph_metrics(graph, max_betweenness_nodes=max_betweenness_nodes)
    write_json(
        str(ir_path(workspace_root, "graph_metrics.json")),
        metrics,
        base_dir=workspace_root,
    )
    if package_name_match:
        dm_records = load_dependency_metadata_records(workspace_root)
        pkg_sub = build_package_subgraph(
            dm_records,
            package_name_match=package_name_match,
            graph=graph,
        )
        write_json(
            str(ir_path(workspace_root, "package_subgraph.json")),
            pkg_sub,
            base_dir=workspace_root,
        )
    return metrics
