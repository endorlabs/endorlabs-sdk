#!/usr/bin/env python3
"""FindingLog weekly CREATE/DELETE analysis for cumulative new-vs-resolved charts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import endorlabs
from endorlabs.workflows.findings.finding_log_trends import (
    build_finding_log_new_vs_resolved_analysis,
)


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
        default=Path(
            ".endorlabs-context/workspace/sessions/agent/exports/new-vs-resolved"
        ),
        help="Directory for analysis JSON.",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=90,
        help="Rolling lookback in calendar days (default: 90).",
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    traverse = not args.no_traverse

    client = endorlabs.Client(tenant=args.namespace, timeout=args.timeout)
    try:
        analysis = build_finding_log_new_vs_resolved_analysis(
            client,
            args.namespace,
            lookback_days=args.lookback_days,
            traverse=traverse,
        )
    finally:
        client.close()

    slug = args.namespace.replace("_", "-")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{slug}-new-vs-resolved-analysis.json"
    out_path.write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    print(
        f"Weeks: {len(analysis['weeks'])} "
        f"({analysis['window_start']} .. {analysis['last_complete_week']}) "
        f"severity_split={analysis['severity_split']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
