#!/usr/bin/env python3
"""Search decoded call graph artifacts safely and deterministically."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
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
    return parser.parse_args()


def _matches_all(text: str, patterns: list[str]) -> bool:
    lowered = text.lower()
    return all(p.lower() in lowered for p in patterns)


def main() -> int:
    """Search decoded call graph nodes and edges and emit results."""
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    callables = json.loads(Path(args.callables).read_text(encoding="utf-8"))
    edges = json.loads(Path(args.edges).read_text(encoding="utf-8"))
    uri_by_id = {row["method_id"]: row["uri"] for row in callables}

    node_hits = [
        row
        for row in callables
        if _matches_all(row.get("uri", ""), args.node_pattern)
    ]

    edge_hits = []
    for edge in edges:
        src_uri = uri_by_id.get(edge["source_id"], edge.get("source_uri", ""))
        tgt_uri = uri_by_id.get(edge["target_id"], edge.get("target_uri", ""))
        if args.source_pattern and not _matches_all(src_uri, args.source_pattern):
            continue
        if args.target_pattern and not _matches_all(tgt_uri, args.target_pattern):
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

    payload = {
        "node_pattern": args.node_pattern,
        "source_pattern": args.source_pattern,
        "target_pattern": args.target_pattern,
        "node_hits_total": len(node_hits),
        "edge_hits_total": len(edge_hits),
        "node_hits": node_hits,
        "edge_hits": edge_hits,
    }

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


if __name__ == "__main__":
    raise SystemExit(main())
