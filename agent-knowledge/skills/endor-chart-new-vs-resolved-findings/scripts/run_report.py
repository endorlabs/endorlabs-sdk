#!/usr/bin/env python3
"""Run FindingLog analysis and generate cumulative weekly canvas."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def run_step(label: str, cmd: list[str]) -> int:
    print(f"\n==> {label}")
    print(" ".join(cmd))
    result = subprocess.run(cmd, check=False)
    return result.returncode


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Query FindingLog weekly CREATE/DELETE counts and render cumulative canvas."
        )
    )
    parser.add_argument(
        "namespace",
        help="Tenant root namespace (traverse includes child namespaces).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            ".endorlabs-context/workspace/sessions/agent/exports/new-vs-resolved"
        ),
        help=(
            "Directory for analysis JSON "
            "(default: .endorlabs-context/workspace/sessions/agent/exports/new-vs-resolved)."
        ),
    )
    parser.add_argument(
        "--canvas-dir",
        type=Path,
        default=None,
        help="Cursor canvases directory (default: auto-detect).",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=90,
        help="Rolling lookback in calendar days (default: 90).",
    )
    parser.add_argument(
        "--analysis-only",
        action="store_true",
        help="Run API analysis only; skip canvas generation.",
    )
    parser.add_argument(
        "--skip-canvas",
        action="store_true",
        help="Skip canvas generation.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    slug = args.namespace.replace("_", "-")
    json_path = args.output_dir / f"{slug}-new-vs-resolved-analysis.json"

    py = sys.executable
    analysis_cmd = [
        py,
        str(SCRIPT_DIR / "run_analysis.py"),
        args.namespace,
        "--output-dir",
        str(args.output_dir),
        "--lookback-days",
        str(args.lookback_days),
    ]
    code = run_step("FindingLog analysis", analysis_cmd)
    if code != 0:
        return code

    if args.analysis_only or args.skip_canvas:
        print(f"\nDone. Analysis JSON: {json_path}")
        return 0

    canvas_cmd = [
        py,
        str(SCRIPT_DIR / "generate_canvas.py"),
        str(json_path),
    ]
    if args.canvas_dir is not None:
        canvas_cmd.extend(["--canvas-dir", str(args.canvas_dir)])
    else:
        canvas_cmd.extend(["--output-dir", str(args.output_dir)])

    code = run_step("Canvas", canvas_cmd)
    if code != 0:
        return code

    print(f"\nDone. Analysis JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
