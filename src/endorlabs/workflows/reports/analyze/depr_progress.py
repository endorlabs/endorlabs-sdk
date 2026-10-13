"""Build dated dependency-resolution progress artifacts from coverage checkpoints."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from endorlabs.context.paths import default_reports_subdir, sanitize_path_segment
from endorlabs.workflows.reports.analyze.depr_coverage import RUN_BUCKET, safe_write
from endorlabs.workflows.reports.export.html.depr_coverage import (
    render_progress_html,
    render_progress_markdown,
)


def load_checkpoint(path: Path) -> dict[str, Any]:
    """Load one dependency-resolution coverage checkpoint."""
    report = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(report, dict)
        or not isinstance(report.get("generated_at"), str)
        or not isinstance(report.get("tenant"), str)
        or not isinstance(report.get("estate"), dict)
        or not isinstance(report.get("by_child_namespace"), list)
    ):
        raise TypeError(f"Not a dependency-resolution checkpoint: {path}")
    return report


def select_checkpoints(
    output_dir: Path,
    tenant: str,
    dates: list[str],
) -> list[Path]:
    """Select the lexically latest checkpoint matching each requested date."""
    slug = sanitize_path_segment(tenant)
    selected = []
    for date in dates:
        if len(date) != 8 or not date.isdigit():
            raise ValueError(f"Checkpoint date must be YYYYMMDD: {date}")
        matches = sorted(
            path
            for path in output_dir.glob(f"{slug}__dr_coverage__{date}*.json")
            if "_progress" not in path.name and "_latest" not in path.name
        )
        if not matches:
            raise FileNotFoundError(
                f"No checkpoint for {tenant!r} on {date} in {output_dir}"
            )
        selected.append(matches[-1])
    return selected


def build_progress_artifacts(
    checkpoints: list[dict],
    out_dir: Path,
    tenant: str,
) -> dict[str, Path]:
    """Write dated JSON, executive Markdown, and HTML progress artifacts."""
    if len(checkpoints) < 2:
        raise ValueError("progress reporting requires at least two checkpoints")
    timestamps = [str(report.get("generated_at") or "") for report in checkpoints]
    if len(set(timestamps)) != len(timestamps):
        raise ValueError("progress checkpoints must have distinct generated_at values")
    checkpoints = sorted(
        checkpoints, key=lambda report: str(report.get("generated_at") or "")
    )
    mismatched = {
        str(report.get("tenant"))
        for report in checkpoints
        if report.get("tenant") != tenant
    }
    if mismatched:
        raise ValueError(
            f"Checkpoint tenant does not match {tenant!r}: {sorted(mismatched)}"
        )
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    slug = sanitize_path_segment(tenant)
    paths = {
        "json": out_dir / f"{slug}__dr_coverage_progress__{timestamp}.json",
        "markdown": out_dir / f"{slug}__dr_coverage_progress_EXEC__{timestamp}.md",
        "html": out_dir / f"{slug}__dr_coverage_progress_EXEC__{timestamp}.html",
    }
    payload = {
        "tenant": tenant,
        "generated_at": timestamp,
        "checkpoint_generated_at": [report["generated_at"] for report in checkpoints],
        "checkpoints": checkpoints,
    }
    safe_write(paths["json"], json.dumps(payload, indent=2) + "\n")
    safe_write(paths["markdown"], render_progress_markdown(checkpoints))
    safe_write(paths["html"], render_progress_html(checkpoints))
    return paths


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build progress reports from dated coverage checkpoints."
    )
    parser.add_argument("-n", "--namespace", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--dates",
        help="Comma-separated checkpoint dates in YYYYMMDD form.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_reports_subdir(RUN_BUCKET),
    )
    source.add_argument(
        "--from-json",
        type=Path,
        nargs="+",
        default=None,
        help="Explicit checkpoint JSON paths instead of date discovery.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.from_json is None:
        dates = [value.strip() for value in args.dates.split(",") if value.strip()]
        if not dates:
            raise ValueError("--dates must contain at least two YYYYMMDD dates")
        paths = select_checkpoints(args.output_dir, args.namespace, dates)
    else:
        paths = args.from_json
    checkpoints = [load_checkpoint(path) for path in paths]
    written = build_progress_artifacts(checkpoints, args.output_dir, args.namespace)
    for kind, path in written.items():
        print(f"Wrote {kind}: {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
