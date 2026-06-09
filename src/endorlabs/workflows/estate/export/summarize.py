#!/usr/bin/env python3
"""Summarize estate workspace IR artifacts (local, no API)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from endorlabs.workflows.estate.workspace.collect_manifest import load_collect_manifest
from endorlabs.workflows.estate.workspace.paths import ir_path, workspace_dir_for

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
    graph = _read_json(ir_path(workspace_root, "compile_dependency_graph.json"))
    partition = _read_json(ir_path(workspace_root, "graph_partition.json"))
    metrics = _read_json(ir_path(workspace_root, "graph_metrics.json"))
    pub = _read_json(ir_path(workspace_root, "publisher_rankings.json"))
    manifest = load_collect_manifest(workspace_root)

    if graph is None:
        msg = f"Missing compile_dependency_graph.json under {workspace_root / 'intermediate-representation'}"
        raise FileNotFoundError(msg)

    node_count = int(graph.get("node_count") or len(graph.get("nodes") or []))
    edge_count = int(graph.get("edge_count") or len(graph.get("edges") or []))
    isolated_count = int(graph.get("isolated_count") or 0)
    isolated_pct = (100.0 * isolated_count / node_count) if node_count else 0.0
    connected_count = sum(1 for n in graph.get("nodes") or [] if not n.get("isolated"))

    partition_summary: dict[str, Any] | None = None
    if partition is not None:
        membership = partition.get("membership") or {}
        by_comm = Counter(membership.values())
        size_dist = Counter(by_comm.values())
        partition_summary = {
            "community_count": partition.get("community_count") or len(by_comm),
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

    top_publishers: list[dict[str, Any]] = []
    if pub is not None:
        for row in (pub.get("rankings") or [])[:5]:
            top_publishers.append(
                {
                    "rank": row.get("rank"),
                    "name": row.get("name"),
                    "consumer_count": row.get("consumer_count"),
                    "inbound_edge_count": row.get("inbound_edge_count"),
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
        "publishers_with_consumers": (
            pub.get("publishers_with_consumers") if pub else None
        ),
        "top_publishers": top_publishers,
        "partition": partition_summary,
        "metrics": metrics_summary,
        "collect_manifest": collect_resources,
        "artifacts_present": {
            "compile_dependency_graph_enriched.json": ir_path(
                workspace_root, "compile_dependency_graph_enriched.json"
            ).is_file(),
            "graph_metrics.json": ir_path(
                workspace_root, "graph_metrics.json"
            ).is_file(),
            "graph_partition.json": ir_path(
                workspace_root, "graph_partition.json"
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
    if summary.get("publishers_with_consumers") is not None:
        lines.append(
            f"publishers_with_consumers={summary['publishers_with_consumers']}"
        )
    part = summary.get("partition")
    if part:
        lines.append(
            "leiden: "
            f"communities={part.get('community_count')} "
            f"singleton_communities={part.get('singleton_communities')} "
            f"multi_node={part.get('multi_node_communities')} "
            f"largest_community={part.get('largest_community')}"
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
    for row in summary.get("top_publishers") or []:
        name = str(row.get("name") or "")[:70]
        lines.append(
            f"  #{row.get('rank')} {name} "
            f"consumers={row.get('consumer_count')} "
            f"inbound={row.get('inbound_edge_count')}"
        )
    return "\n".join(lines)


# Backward alias for tests migrating from session layout
summarize_session_dir = summarize_workspace_dir


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Summarize estate workspace IR artifacts.")
    p.add_argument(
        "--namespace",
        action="append",
        required=True,
        dest="namespaces",
        metavar="NAMESPACE",
    )
    p.add_argument("--workspace", action="append", dest="workspaces", default=[])
    p.add_argument(
        "--date",
        help="UTC YYYYMMDD suffix when resolving workspace from namespace",
    )
    p.add_argument("--json", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summaries: list[dict[str, Any]] = []
    exit_code = 0
    if args.workspaces:
        for workspace in args.workspaces:
            workspace_root = Path(workspace)
            try:
                summaries.append(summarize_workspace_dir(workspace_root))
            except FileNotFoundError as exc:
                print(str(exc), file=sys.stderr)
                exit_code = 1
    else:
        for namespace in args.namespaces:
            workspace_root = workspace_dir_for(
                ".endorlabs-context", namespace, date_suffix=args.date
            )
            try:
                summaries.append(
                    summarize_workspace_dir(workspace_root, namespace=namespace)
                )
            except FileNotFoundError as exc:
                print(str(exc), file=sys.stderr)
                exit_code = 1

    if args.json:
        print(json.dumps(summaries, indent=2))
    else:
        for summary in summaries:
            print(format_summary_text(summary))
            print()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
