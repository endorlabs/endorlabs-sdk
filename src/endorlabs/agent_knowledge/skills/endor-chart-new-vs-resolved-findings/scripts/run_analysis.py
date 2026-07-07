#!/usr/bin/env python3
"""FindingLog weekly CREATE/DELETE analysis for cumulative new-vs-resolved charts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import endorlabs
from endorlabs.context.paths import default_runs_dir
from endorlabs.workflows.findings.finding_log_trends import (
    build_finding_log_new_vs_resolved_analysis,
)

RUN_BUCKET = "finding-log-weekly-trends"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Query FindingLog CREATE/DELETE weekly counts and write analysis JSON."
        )
    )
    parser.add_argument(
        "namespace",
        help="Tenant root or child namespace (--traverse includes children).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_runs_dir(RUN_BUCKET),
        help="Directory for analysis JSON (default: workspace/runs/finding-log-weekly-trends/).",
    )
    parser.add_argument(
        "--interval",
        default="week",
        help=(
            "group_by_time interval alias (default: week). "
            "Same values as endorctl / ListParameters.group_by_time_interval."
        ),
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=13,
        help=(
            "Number of complete interval buckets before the current bucket "
            "(default: 13 weeks ≈ past quarter)."
        ),
    )
    parser.add_argument(
        "--no-traverse",
        action="store_true",
        help="List only the namespace path (omit child namespaces).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="SDK read timeout in seconds per request (default: 120).",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=12,
        help="Parallel workers when aggregate query falls back to project shards.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    traverse = not args.no_traverse

    client = endorlabs.Client(tenant=args.namespace, timeout=args.timeout)
    try:
        analysis = build_finding_log_new_vs_resolved_analysis(
            client,
            args.namespace,
            interval=args.interval,
            lookback=args.lookback,
            traverse=traverse,
            max_workers=args.max_workers,
        )
    finally:
        client.close()

    slug = args.namespace.replace("_", "-")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{slug}-new-vs-resolved-analysis.json"
    out_path.write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    print(
        f"Buckets: {len(analysis['weeks'])} "
        f"interval={analysis['interval']} lookback={analysis['lookback']} "
        f"({analysis['window_start']} .. {analysis['last_complete_week']}) "
        f"severity_split={analysis['severity_split']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
