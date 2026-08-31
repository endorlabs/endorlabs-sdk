"""Run PRF analysis and generate canvas + PDF report artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from endorlabs.context.paths import default_reports_subdir
from endorlabs.workflows.reports.analyze.prf_report_analysis import (
    main as analysis_main,
)
from endorlabs.workflows.reports.export.canvas.prf_canvas import main as canvas_main
from endorlabs.workflows.reports.export.canvas.prf_pdf import main as pdf_main

RUN_BUCKET = "prf-analysis"


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
        default=default_reports_subdir(RUN_BUCKET),
        help=(
            f"Directory for JSON, HTML, and PDF "
            f"(default: {default_reports_subdir(RUN_BUCKET).as_posix()}/)."
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

    analysis_argv = [args.tenant, "--output-dir", str(args.output_dir)]
    print("\n==> PRF analysis")
    code = analysis_main(analysis_argv)
    if code != 0:
        return code

    if args.analysis_only:
        return 0

    if not args.skip_canvas:
        canvas_argv = [str(json_path)]
        if args.canvas_dir is not None:
            canvas_argv.extend(["--canvas-dir", str(args.canvas_dir)])
        else:
            canvas_argv.extend(["--output-dir", str(args.output_dir)])
        print("\n==> Canvas")
        code = canvas_main(canvas_argv)
        if code != 0:
            return code

    if not args.skip_pdf:
        pdf_argv = [
            str(json_path),
            "--output-dir",
            str(args.output_dir),
        ]
        if args.chrome is not None:
            pdf_argv.extend(["--chrome", str(args.chrome)])
        if args.html_only:
            pdf_argv.append("--html-only")
        label = "HTML" if args.html_only else "HTML + PDF"
        print(f"\n==> {label}")
        code = pdf_main(pdf_argv)
        if code != 0:
            return code

    print(f"\nDone. Analysis JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
