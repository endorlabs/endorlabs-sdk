#!/usr/bin/env python3
"""Summarize estate workspace IR artifacts (local, no API)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from endorlabs.workflows.estate.contracts.ir_artifacts import (
    CLUSTERING_GRAPH_IR,
    COMMUNITY_DETECTION_IR,
    COMMUNITY_PROFILES_IR,
    COMPILE_DEPENDENCY_GRAPH_ENRICHED_IR,
    COMPILE_DEPENDENCY_GRAPH_IR,
    GRAPH_METRICS_IR,
    PRODUCER_RANKINGS_IR,
)
from endorlabs.workflows.estate.workspace.collect_manifest import load_collect_manifest
from endorlabs.workflows.estate.workspace.paths import ir_path

SUMMARY_SCHEMA = "endor.workspace_summary.v1"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def summarize_workspace_dir(
    workspace_root: Path, *, namespace: str | None = None
) -> dict[str, Any]:
    """Build a machine-readable summary from on-disk workspace IR."""
    graph = _read_json(ir_path(workspace_root, COMPILE_DEPENDENCY_GRAPH_IR))
    community_detection = _read_json(ir_path(workspace_root, COMMUNITY_DETECTION_IR))
    metrics = _read_json(ir_path(workspace_root, GRAPH_METRICS_IR))
    producers = _read_json(ir_path(workspace_root, PRODUCER_RANKINGS_IR))
    manifest = load_collect_manifest(workspace_root)

    if graph is None:
        msg = f"Missing {COMPILE_DEPENDENCY_GRAPH_IR} under {workspace_root / 'intermediate-representation'}"
        raise FileNotFoundError(msg)

    node_count = int(graph.get("node_count") or len(graph.get("nodes") or []))
    edge_count = int(graph.get("edge_count") or len(graph.get("edges") or []))
    isolated_count = int(graph.get("isolated_count") or 0)
    isolated_pct = (100.0 * isolated_count / node_count) if node_count else 0.0
    connected_count = sum(1 for n in graph.get("nodes") or [] if not n.get("isolated"))

    community_detection_summary: dict[str, Any] | None = None
    if community_detection is not None:
        membership = community_detection.get("membership") or {}
        by_comm = Counter(membership.values())
        size_dist = Counter(by_comm.values())
        community_detection_summary = {
            "method": community_detection.get("method"),
            "resolution": community_detection.get("resolution"),
            "edge_weight_source": community_detection.get("edge_weight_source"),
            "vertex_weight_source": community_detection.get("vertex_weight_source"),
            "community_count": community_detection.get("community_count")
            or len(by_comm),
            "singleton_communities": size_dist.get(1, 0),
            "multi_node_communities": sum(1 for size in by_comm.values() if size > 1),
            "largest_community": max(by_comm.values()) if by_comm else 0,
        }

    metrics_summary: dict[str, Any] | None = None
    if metrics is not None:
        components = metrics.get("components") or {}
        scc = metrics.get("scc") or {}
        k_core = metrics.get("k_core") or {}
        wcc_sizes = components.get("weakly_connected_sizes") or []
        centrality = metrics.get("centrality") or {}
        metrics_summary = {
            "weakly_connected_components": components.get("weakly_connected_count"),
            "largest_weak_component": wcc_sizes[0] if wcc_sizes else None,
            "strongly_connected_components": components.get("strongly_connected_count"),
            "has_cycles": scc.get("has_cycles"),
            "k_core_max": k_core.get("max_k"),
            "nodes_at_max_k": len(k_core.get("nodes_at_max_k") or []),
            "betweenness_skipped": centrality.get("betweenness_skipped"),
        }

    top_producers: list[dict[str, Any]] = []
    if producers is not None:
        for row in (producers.get("rankings") or [])[:5]:
            top_producers.append(
                {
                    "rank": row.get("rank"),
                    "name": row.get("name"),
                    "importer_count": row.get("importer_count"),
                    "inbound_import_count": row.get("inbound_import_count"),
                }
            )

    collect_resources = None
    if manifest is not None:
        collect_resources = {
            rid: {
                "status": rec.status,
                "line_count": rec.line_count,
            }
            for rid, rec in manifest.resources.items()
        }

    ns = namespace or (manifest.namespace if manifest else workspace_root.name)
    return {
        "schema": SUMMARY_SCHEMA,
        "namespace": ns,
        "workspace_root": str(workspace_root),
        "graph": {
            "node_count": node_count,
            "edge_count": edge_count,
            "isolated_count": isolated_count,
            "isolated_percent": round(isolated_pct, 1),
            "connected_count": connected_count,
        },
        "producers_with_importers": (
            producers.get("producers_with_importers") if producers else None
        ),
        "top_producers": top_producers,
        "community_detection": community_detection_summary,
        "metrics": metrics_summary,
        "collect_manifest": collect_resources,
        "artifacts_present": {
            COMPILE_DEPENDENCY_GRAPH_ENRICHED_IR: ir_path(
                workspace_root, COMPILE_DEPENDENCY_GRAPH_ENRICHED_IR
            ).is_file(),
            GRAPH_METRICS_IR: ir_path(workspace_root, GRAPH_METRICS_IR).is_file(),
            CLUSTERING_GRAPH_IR: ir_path(workspace_root, CLUSTERING_GRAPH_IR).is_file(),
            COMMUNITY_DETECTION_IR: ir_path(
                workspace_root, COMMUNITY_DETECTION_IR
            ).is_file(),
            COMMUNITY_PROFILES_IR: ir_path(
                workspace_root, COMMUNITY_PROFILES_IR
            ).is_file(),
            "risk_cardinality.json": ir_path(
                workspace_root, "risk_cardinality.json"
            ).is_file(),
            "version_cardinality.json": ir_path(
                workspace_root, "version_cardinality.json"
            ).is_file(),
            "estate_dashboard.html": (
                workspace_root / "viz" / "estate_dashboard.html"
            ).is_file(),
        },
    }


def format_summary_text(summary: dict[str, Any]) -> str:
    """Human-readable multi-line summary for one workspace."""
    ns = summary.get("namespace") or "unknown"
    g = summary.get("graph") or {}
    lines = [
        f"=== {ns} ===",
        (
            f"nodes={g.get('node_count')} edges={g.get('edge_count')} "
            f"isolated={g.get('isolated_count')} ({g.get('isolated_percent')}%) "
            f"connected={g.get('connected_count')}"
        ),
    ]
    if summary.get("producers_with_importers") is not None:
        lines.append(f"producers_with_importers={summary['producers_with_importers']}")
    detection = summary.get("community_detection")
    if detection:
        lines.append(
            "groups: "
            f"method={detection.get('method')} "
            f"resolution={detection.get('resolution')} "
            f"communities={detection.get('community_count')} "
            f"singleton_communities={detection.get('singleton_communities')} "
            f"multi_node={detection.get('multi_node_communities')} "
            f"largest_community={detection.get('largest_community')}"
        )
    metrics = summary.get("metrics")
    if metrics:
        lines.append(
            "metrics: "
            f"wcc={metrics.get('weakly_connected_components')} "
            f"largest_wcc={metrics.get('largest_weak_component')} "
            f"k_core_max={metrics.get('k_core_max')} "
            f"cycles={metrics.get('has_cycles')}"
        )
    for row in summary.get("top_producers") or []:
        name = str(row.get("name") or "")[:70]
        lines.append(
            f"  #{row.get('rank')} {name} "
            f"importers={row.get('importer_count')} "
            f"inbound={row.get('inbound_import_count')}"
        )
    return "\n".join(lines)
