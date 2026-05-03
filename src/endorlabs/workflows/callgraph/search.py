"""Search decoded call graph artifacts safely and deterministically."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


def _matches_all(text: str, patterns: list[str]) -> bool:
    lowered = text.lower()
    return all(p.lower() in lowered for p in patterns)


def search_decoded_call_graph(
    callables: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    node_patterns: list[str],
    source_patterns: list[str],
    target_patterns: list[str],
) -> dict[str, Any]:
    """Filter decoded callables/edges by URI substring patterns (case-insensitive)."""
    uri_by_id = {row["method_id"]: row["uri"] for row in callables}

    node_hits = [
        row for row in callables if _matches_all(row.get("uri", ""), node_patterns)
    ]

    edge_hits: list[dict[str, Any]] = []
    for edge in edges:
        src_uri = uri_by_id.get(edge["source_id"], edge.get("source_uri", ""))
        tgt_uri = uri_by_id.get(edge["target_id"], edge.get("target_uri", ""))
        if source_patterns and not _matches_all(src_uri, source_patterns):
            continue
        if target_patterns and not _matches_all(tgt_uri, target_patterns):
            continue
        edge_hits.append(
            {
                "source_id": edge["source_id"],
                "target_id": edge["target_id"],
                "source_uri": src_uri,
                "target_uri": tgt_uri,
                "call_types": edge.get("call_types", []),
                "callsite_count": edge.get("callsite_count", 0),
            }
        )

    return {
        "node_pattern": node_patterns,
        "source_pattern": source_patterns,
        "target_pattern": target_patterns,
        "node_hits_total": len(node_hits),
        "edge_hits_total": len(edge_hits),
        "node_hits": node_hits,
        "edge_hits": edge_hits,
    }


def parse_search_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for call graph search."""
    parser = argparse.ArgumentParser(description="Search decoded call graph files.")
    parser.add_argument(
        "--callables", required=True, help="Path to decoded_callables.json"
    )
    parser.add_argument("--edges", required=True, help="Path to decoded_edges.json")
    parser.add_argument(
        "--node-pattern",
        action="append",
        default=[],
        help="Case-insensitive substring pattern for node URI filtering. Repeatable.",
    )
    parser.add_argument(
        "--source-pattern",
        action="append",
        default=[],
        help="Case-insensitive source URI pattern for edge filtering. Repeatable.",
    )
    parser.add_argument(
        "--target-pattern",
        action="append",
        default=[],
        help="Case-insensitive target URI pattern for edge filtering. Repeatable.",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Optional output JSON path. Prints to stdout if omitted.",
    )
    return parser.parse_args(argv)


def run_search_main(argv: list[str] | None = None) -> int:
    """CLI entry: load JSON files and emit search results."""
    args = parse_search_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    callables = json.loads(Path(args.callables).read_text(encoding="utf-8"))
    edges = json.loads(Path(args.edges).read_text(encoding="utf-8"))
    payload = search_decoded_call_graph(
        callables,
        edges,
        node_patterns=args.node_pattern,
        source_patterns=args.source_pattern,
        target_patterns=args.target_pattern,
    )

    if args.out:
        Path(args.out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        LOGGER.info("Wrote search output: %s", args.out)
    else:
        LOGGER.info("node_hits_total=%s", payload["node_hits_total"])
        LOGGER.info("edge_hits_total=%s", payload["edge_hits_total"])
        LOGGER.info("Provide --out to persist full search results.")
    return 0


def main() -> int:
    """``python -m endorlabs.workflows.callgraph.search`` entrypoint."""
    return run_search_main()


if __name__ == "__main__":
    raise SystemExit(main())
