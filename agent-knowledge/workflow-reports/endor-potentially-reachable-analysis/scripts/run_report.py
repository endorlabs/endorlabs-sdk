#!/usr/bin/env python3
"""Run PRF analysis and generate canvas + PDF report artifacts."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from endorlabs.context.paths import default_runs_dir

SCRIPT_DIR = Path(__file__).resolve().parent
RUN_BUCKET = "potentially-reachable-analysis"


def run_step(label: str, cmd: list[str]) -> int:
    print(f"\n==> {label}")
    print(" ".join(cmd))
    result = subprocess.run(cmd, check=False)
    return result.returncode


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Query PRF findings + PV resolution errors, then render canvas and PDF."
        )
    )
    parser.add_argument(
        "tenant",
        help="Tenant root namespace (traverse includes child namespaces).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_runs_dir(RUN_BUCKET),
        help=(
            "Directory for JSON, HTML, and PDF "
            "(default: workspace/runs/potentially-reachable-analysis/)."
        ),
    )
    parser.add_argument(
        "--canvas-dir",
        type=Path,
        default=None,
        help="Cursor canvases directory (default: auto-detect).",
    )
    parser.add_argument(
        "--chrome",
        type=Path,
        default=None,
        help="Chrome/Chromium binary for PDF rendering.",
    )
    parser.add_argument(
        "--skip-canvas",
        action="store_true",
        help="Skip canvas generation.",
    )
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Skip HTML and PDF generation entirely.",
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Write HTML only (no PDF).",
    )
    parser.add_argument(
        "--analysis-only",
        action="store_true",
        help="Run API analysis only; skip canvas and PDF.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    json_path = args.output_dir / f"{args.tenant}-prf-analysis.json"

    py = sys.executable
    analysis_cmd = [
        py,
        str(SCRIPT_DIR / "run_analysis.py"),
        args.tenant,
        "--output-dir",
        str(args.output_dir),
    ]
    code = run_step("PRF analysis", analysis_cmd)
    if code != 0:
        return code

    if args.analysis_only:
        return 0

    if not args.skip_canvas:
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

    if not args.skip_pdf:
        pdf_cmd = [
            py,
            str(SCRIPT_DIR / "generate_report_pdf.py"),
            str(json_path),
            "--output-dir",
            str(args.output_dir),
        ]
        if args.chrome is not None:
            pdf_cmd.extend(["--chrome", str(args.chrome)])
        if args.html_only:
            pdf_cmd.append("--html-only")
        label = "HTML" if args.html_only else "HTML + PDF"
        code = run_step(label, pdf_cmd)
        if code != 0:
            return code

    print(f"\nDone. Analysis JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
