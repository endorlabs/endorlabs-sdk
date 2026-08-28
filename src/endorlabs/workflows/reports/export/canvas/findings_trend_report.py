"""Run FindingLog analysis and generate cumulative weekly canvas."""

from __future__ import annotations

import argparse
from pathlib import Path

from endorlabs.context.paths import default_reports_subdir
from endorlabs.workflows.reports.analyze.findings_chart_analysis import (
    main as analysis_main,
)
from endorlabs.workflows.reports.export.canvas.findings_trend_canvas import (
    main as canvas_main,
)

RUN_BUCKET = "findings-trend"


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
        default=default_reports_subdir(RUN_BUCKET),
        help=(
            f"Directory for analysis JSON "
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
        "--interval",
        default="week",
        help="group_by_time interval alias (default: week).",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=13,
        help="Complete interval buckets to include (default: 13).",
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

    analysis_argv = [
        args.namespace,
        "--output-dir",
        str(args.output_dir),
        "--interval",
        args.interval,
        "--lookback",
        str(args.lookback),
    ]
    print("\n==> FindingLog analysis")
    code = analysis_main(analysis_argv)
    if code != 0:
        return code

    if args.analysis_only or args.skip_canvas:
        print(f"\nDone. Analysis JSON: {json_path}")
        return 0

    canvas_argv = [str(json_path)]
    if args.canvas_dir is not None:
        canvas_argv.extend(["--canvas-dir", str(args.canvas_dir)])
    else:
        canvas_argv.extend(["--output-dir", str(args.output_dir)])

    print("\n==> Canvas")
    code = canvas_main(canvas_argv)
    if code != 0:
        return code

    print(f"\nDone. Analysis JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
