#!/usr/bin/env python3
"""Summarize compile-dependency-graph session artifacts (local, no API)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from endorlabs.workflows.relationships.dependency_graph import session_dir_for

SUMMARY_SCHEMA = "endor.graph_session_summary.v1"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def _phase_validations(session_dir: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for path in sorted(session_dir.glob("phase_*_validation.json")):
        name = path.name.removeprefix("phase_").removesuffix("_validation.json")
        payload = _read_json(path)
        if payload is not None:
            out[name] = bool(payload.get("ok"))
    return out


def summarize_session_dir(session_dir: Path, *, namespace: str) -> dict[str, Any]:
    """Build a machine-readable summary from on-disk graph session artifacts."""
    graph = _read_json(session_dir / "compile_dependency_graph.json")
    partition = _read_json(session_dir / "graph_partition.json")
    metrics = _read_json(session_dir / "graph_metrics.json")
    pub = _read_json(session_dir / "publisher_rankings.json")

    if graph is None:
        msg = f"Missing compile_dependency_graph.json under {session_dir}"
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

    return {
        "schema": SUMMARY_SCHEMA,
        "namespace": namespace,
        "session_dir": str(session_dir),
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
        "phase_validation": _phase_validations(session_dir),
        "artifacts_present": {
            "compile_dependency_graph_enriched.json": (
                session_dir / "compile_dependency_graph_enriched.json"
            ).is_file(),
            "graph_metrics.json": (session_dir / "graph_metrics.json").is_file(),
            "graph_partition.json": (session_dir / "graph_partition.json").is_file(),
            "community_summary.json": (
                session_dir / "community_summary.json"
            ).is_file(),
            "dependency_corpus.jsonl": (
                session_dir / "dependency_corpus.jsonl"
            ).is_file(),
        },
    }


def format_summary_text(summary: dict[str, Any]) -> str:
    """Human-readable multi-line summary for one session."""
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
    failed = [
        phase for phase, ok in (summary.get("phase_validation") or {}).items() if not ok
    ]
    if failed:
        lines.append(f"phase_validation_failed: {', '.join(failed)}")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Summarize compile-dependency-graph session artifacts "
            "(no API; reads .endorlabs-context/session/<slug>/)."
        )
    )
    p.add_argument(
        "--namespace",
        action="append",
        required=True,
        dest="namespaces",
        metavar="NAMESPACE",
        help="Estate namespace (repeat for multiple sessions).",
    )
    p.add_argument(
        "--context-dir",
        default=".endorlabs-context",
        help="Context root containing session/<slug>/ directories.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of text.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summaries: list[dict[str, Any]] = []
    exit_code = 0
    for namespace in args.namespaces:
        session_dir = session_dir_for(args.context_dir, namespace)
        try:
            summaries.append(summarize_session_dir(session_dir, namespace=namespace))
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
