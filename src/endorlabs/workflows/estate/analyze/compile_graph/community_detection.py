"""Community detection on compile-import graphs (Leiden modularity backend)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from endorlabs.workflows.estate.contracts.ir_artifacts import (
    CLUSTERING_GRAPH_IR,
    COMMUNITY_DETECTION_SCHEMA,
    COMMUNITY_PROFILES_SCHEMA,
    COMPILE_DEPENDENCY_GRAPH_ENRICHED_IR,
    COMPILE_DEPENDENCY_GRAPH_IR,
)
from endorlabs.workflows.estate.workspace.paths import ir_path

EdgeWeightSource = Literal["none", "import_evidence_count"]
VertexWeightSource = Literal["none", "inbound_import_count"]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class CommunityDetectionCheck:
    """One validation check for community detection."""

    name: str
    ok: bool
    detail: str = ""


@dataclass
class CommunityDetectionValidation:
    """Validation report for community detection."""

    ok: bool
    checks: list[CommunityDetectionCheck] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": "detect_communities",
            "ok": self.ok,
            "generated_at": self.generated_at,
            "checks": [
                {"name": c.name, "ok": c.ok, "detail": c.detail} for c in self.checks
            ],
        }


@dataclass(frozen=True, slots=True)
class CommunityDetectionOptions:
    """Community detection tuning knobs (Leiden RBConfiguration backend)."""

    resolution: float = 1.0
    iterations: int = 10
    edge_weight_source: EdgeWeightSource = "none"
    vertex_weight_source: VertexWeightSource = "none"
    component_min_size: int = 1
    seed: int = 42


def _vertex_weights_for_detection(
    import_graph: dict[str, Any],
    *,
    vertex_weight_source: VertexWeightSource,
) -> list[float] | None:
    if vertex_weight_source == "none":
        return None
    nodes = import_graph.get("nodes") or []
    if vertex_weight_source == "inbound_import_count":
        in_deg = {int(n["node_id"]): int(n.get("in_degree") or 0) for n in nodes}
        ordered_ids = [int(n["node_id"]) for n in nodes if "node_id" in n]
        return [float(max(1, in_deg.get(i, 0))) for i in ordered_ids]
    return None


def _edge_weights_for_detection(
    import_graph: dict[str, Any],
    *,
    edge_weight_source: EdgeWeightSource,
) -> list[float] | None:
    if edge_weight_source != "import_evidence_count":
        return None
    edges = import_graph.get("edges") or []
    return [float(max(1, e.get("import_evidence_count") or 1)) for e in edges]


def build_community_profiles(
    import_graph: dict[str, Any],
    communities: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate leadership/AppSec-oriented fields per detected community."""
    nodes = import_graph.get("nodes") or []
    edges = import_graph.get("edges") or []
    node_by_id = {int(n["node_id"]): n for n in nodes if "node_id" in n}
    rows: list[dict[str, Any]] = []
    for comm in communities:
        node_ids = [int(i) for i in comm.get("node_ids") or []]
        comm_nodes = [node_by_id[i] for i in node_ids if i in node_by_id]
        namespaces: dict[str, int] = {}
        tags: dict[str, int] = {}
        linking_packages: dict[str, int] = {}
        in_deg: dict[int, int] = {}
        for edge in edges:
            producer_id = int(edge.get("producer_vertex_id", -1))
            if producer_id in node_ids:
                in_deg[producer_id] = in_deg.get(producer_id, 0) + 1
                pkg = str(edge.get("linking_package_name") or "")
                if pkg:
                    linking_packages[pkg] = linking_packages.get(pkg, 0) + 1
        for node in comm_nodes:
            for ns in node.get("namespaces") or [node.get("namespace")]:
                if ns:
                    namespaces[str(ns)] = namespaces.get(str(ns), 0) + 1
            for tag in node.get("tags") or []:
                tags[str(tag)] = tags.get(str(tag), 0) + 1
        hub_ids = sorted(in_deg.items(), key=lambda x: (-x[1], x[0]))[:10]
        rows.append(
            {
                "community_id": comm.get("community_id"),
                "node_count": len(node_ids),
                "edge_count": sum(
                    1
                    for e in edges
                    if int(e.get("importer_vertex_id", -1)) in node_ids
                    and int(e.get("producer_vertex_id", -1)) in node_ids
                ),
                "dominant_namespaces": sorted(
                    namespaces.items(), key=lambda x: (-x[1], x[0])
                )[:5],
                "top_tags": sorted(tags.items(), key=lambda x: (-x[1], x[0]))[:5],
                "top_linking_packages": sorted(
                    linking_packages.items(), key=lambda x: (-x[1], x[0])
                )[:10],
                "hub_importer_vertex_ids": [i for i, _ in hub_ids],
            }
        )
    return {
        "schema": COMMUNITY_PROFILES_SCHEMA,
        "namespace": import_graph.get("namespace"),
        "generated_at": _utc_now(),
        "communities": rows,
    }


def load_clustering_graph_input(
    root: Path,
    *,
    use_intermediate_representation: bool = True,
) -> dict[str, Any]:
    """Load enriched import graph, preferring ``clustering_graph.json`` when present."""

    def _artifact_path(name: str) -> Path:
        if use_intermediate_representation:
            return ir_path(root, name)
        return root / name

    clustering_path = _artifact_path(CLUSTERING_GRAPH_IR)
    if clustering_path.is_file():
        clustering = json.loads(clustering_path.read_text(encoding="utf-8"))
        nodes = []
        for item in clustering.get("nodes") or []:
            nodes.append(
                {
                    "node_id": item.get("id"),
                    "project_uuid": item.get("name"),
                    "name": item.get("name"),
                }
            )
        edges = [
            {
                "importer_vertex_id": e.get("importer"),
                "producer_vertex_id": e.get("producer"),
                "linking_package_name": e.get("linking_package_name"),
                "import_evidence_count": e.get("import_evidence_count"),
            }
            for e in clustering.get("edges") or []
        ]
        enriched_path = _artifact_path(COMPILE_DEPENDENCY_GRAPH_ENRICHED_IR)
        base = {}
        if enriched_path.is_file():
            base = json.loads(enriched_path.read_text(encoding="utf-8"))
        return {
            **base,
            "namespace": clustering.get("namespace") or base.get("namespace"),
            "nodes": base.get("nodes") or nodes,
            "edges": base.get("edges") or edges,
        }
    enriched_path = _artifact_path(COMPILE_DEPENDENCY_GRAPH_ENRICHED_IR)
    if enriched_path.is_file():
        return json.loads(enriched_path.read_text(encoding="utf-8"))
    return json.loads(
        _artifact_path(COMPILE_DEPENDENCY_GRAPH_IR).read_text(encoding="utf-8")
    )


def detect_communities(
    import_graph: dict[str, Any],
    *,
    options: CommunityDetectionOptions | None = None,
) -> tuple[dict[str, Any], CommunityDetectionValidation, dict[str, Any]]:
    """Detect project communities on a compile-import graph."""
    try:
        import igraph as ig  # pyright: ignore[reportMissingTypeStubs]
        import leidenalg  # pyright: ignore[reportMissingTypeStubs]
    except ImportError:
        validation = CommunityDetectionValidation(
            ok=False,
            checks=[
                CommunityDetectionCheck(
                    "igraph_leidenalg_installed",
                    False,
                    "Install optional extra: uv sync --extra graph",
                )
            ],
            generated_at=_utc_now(),
        )
        return {}, validation, {}

    opts = options or CommunityDetectionOptions()
    nodes = import_graph.get("nodes") or []
    edges = import_graph.get("edges") or []
    if not nodes:
        validation = CommunityDetectionValidation(
            ok=False,
            checks=[CommunityDetectionCheck("node_count_gt_zero", False, "0 nodes")],
            generated_at=_utc_now(),
        )
        return {}, validation, {}

    graph_node_ids = [int(node["node_id"]) for node in nodes if "node_id" in node]
    id_to_idx = {nid: i for i, nid in enumerate(graph_node_ids)}

    g = ig.Graph(directed=True)
    g.add_vertices(len(graph_node_ids))
    e_pairs = []
    edge_index_map: list[int] = []
    for i, e in enumerate(edges):
        importer_id = int(e["importer_vertex_id"])
        producer_id = int(e["producer_vertex_id"])
        if importer_id in id_to_idx and producer_id in id_to_idx:
            e_pairs.append((id_to_idx[importer_id], id_to_idx[producer_id]))
            edge_index_map.append(i)
    if e_pairs:
        g.add_edges(e_pairs)
        ew = _edge_weights_for_detection(
            import_graph, edge_weight_source=opts.edge_weight_source
        )
        if ew is not None:
            g.es["weight"] = [ew[i] for i in edge_index_map]

    if opts.component_min_size > 1:
        wcc = g.components(mode="weak")
        largest = max(wcc, key=len)
        if len(largest) < opts.component_min_size:
            validation = CommunityDetectionValidation(
                ok=False,
                checks=[
                    CommunityDetectionCheck(
                        "largest_wcc_min_size",
                        False,
                        f"largest component size {len(largest)} < {opts.component_min_size}",
                    )
                ],
                generated_at=_utc_now(),
            )
            return {}, validation, {}

    vertex_weights = _vertex_weights_for_detection(
        import_graph, vertex_weight_source=opts.vertex_weight_source
    )
    edge_weights_attr = "weight" if g.es and "weight" in g.es.attributes() else None
    partition_kwargs: dict[str, Any] = {
        "resolution_parameter": opts.resolution,
    }
    if vertex_weights is not None:
        partition_type = leidenalg.RBERVertexPartition
        partition_kwargs["node_sizes"] = vertex_weights
        if edge_weights_attr is not None:
            partition_kwargs["weights"] = edge_weights_attr
    else:
        partition_type = leidenalg.RBConfigurationVertexPartition
        if edge_weights_attr is not None:
            partition_kwargs["weights"] = edge_weights_attr

    partition = leidenalg.find_partition(
        g,
        partition_type,
        n_iterations=opts.iterations,
        seed=opts.seed,
        **partition_kwargs,
    )
    membership = {graph_node_ids[i]: int(m) for i, m in enumerate(partition.membership)}
    communities: dict[int, list[int]] = {}
    for node_id, comm in membership.items():
        communities.setdefault(comm, []).append(node_id)

    id_to_uuid = {int(n["node_id"]): str(n.get("project_uuid") or "") for n in nodes}
    community_rows = []
    for comm_id, comm_node_ids in sorted(communities.items()):
        uuids = [id_to_uuid[i] for i in sorted(comm_node_ids) if i in id_to_uuid]
        community_rows.append(
            {
                "community_id": comm_id,
                "node_ids": sorted(comm_node_ids),
                "project_uuids": uuids,
            }
        )

    payload = {
        "method": "modularity_leiden"
        if partition_type is leidenalg.RBConfigurationVertexPartition
        else "potts_leiden",
        "schema": COMMUNITY_DETECTION_SCHEMA,
        "seed": opts.seed,
        "resolution": opts.resolution,
        "iterations": opts.iterations,
        "edge_weight_source": opts.edge_weight_source,
        "vertex_weight_source": opts.vertex_weight_source,
        "generated_at": _utc_now(),
        "node_count": len(graph_node_ids),
        "edge_count": len(e_pairs),
        "isolated_count": import_graph.get("isolated_count", 0),
        "community_count": len(community_rows),
        "membership": {str(k): v for k, v in membership.items()},
        "communities": community_rows,
    }
    profiles = build_community_profiles(import_graph, community_rows)
    checks = [
        CommunityDetectionCheck(
            "membership_complete",
            len(membership) == len(graph_node_ids),
            f"{len(membership)} membership / {len(graph_node_ids)} nodes",
        ),
        CommunityDetectionCheck(
            "community_count_gt_zero",
            len(community_rows) > 0,
            f"{len(community_rows)} communities",
        ),
    ]
    validation = CommunityDetectionValidation(
        ok=all(c.ok for c in checks),
        checks=checks,
        generated_at=_utc_now(),
    )
    return payload, validation, profiles
