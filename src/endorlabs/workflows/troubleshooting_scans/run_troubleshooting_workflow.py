"""Run the full troubleshooting-scans workflow end-to-end."""

from __future__ import annotations

import argparse
from types import SimpleNamespace

from . import (
    diff_scans,
    fetch_scan_logs,
    fetch_scan_results,
    resolve_projects,
    select_anomalous_scans,
)
from .common import default_troubleshooting_output_dir, load_json, root_tenant


def build_parser() -> argparse.ArgumentParser:
    """Build argparse parser for this workflow CLI."""
    parser = argparse.ArgumentParser(description="Run full troubleshooting workflow")
    _ = parser.add_argument("--tenant", required=True)
    _ = parser.add_argument("--namespace")
    _ = parser.add_argument("--project-uuid")
    _ = parser.add_argument("--project-name")
    _ = parser.add_argument("--project-url")
    _ = parser.add_argument("--project-name-regex")
    _ = parser.add_argument("--limit", type=int, default=25)
    _ = parser.add_argument(
        "--scan-window", type=int, help="Optional alias for --limit."
    )
    _ = parser.add_argument("--status-filter")
    _ = parser.add_argument(
        "--pair-mode",
        choices=["adjacent", "best-anomaly", "latest"],
        default="best-anomaly",
    )
    _ = parser.add_argument("--min-delta-findings", type=int, default=10)
    _ = parser.add_argument("--min-delta-deps", type=int, default=50)
    _ = parser.add_argument("--max-log-entries", type=int, default=500)
    _ = parser.add_argument(
        "--regression-only",
        action="store_true",
        help="Check latest pair for regression and pull logs only on regression.",
    )
    _ = parser.add_argument(
        "--emit-diff",
        action="store_true",
        help="When used with --regression-only, also generate diff report.",
    )
    _ = parser.add_argument(
        "--output-dir", default=default_troubleshooting_output_dir()
    )
    _ = parser.add_argument("--timestamped", action="store_true")
    return parser


def main() -> int:
    """Run the module CLI and return exit code."""
    args = build_parser().parse_args()
    ns = args.namespace or args.tenant
    root = root_tenant(ns)
    effective_limit = args.scan_window or args.limit
    selected_pair_mode = "latest" if args.regression_only else args.pair_mode

    step1 = resolve_projects.run(
        SimpleNamespace(
            tenant=args.tenant,
            namespace=ns,
            project_uuid=args.project_uuid,
            project_name=args.project_name,
            project_url=args.project_url,
            project_name_regex=args.project_name_regex,
            output_dir=args.output_dir,
            timestamped=args.timestamped,
        )
    )
    project_payload = load_json(step1["artifact"])
    projects = project_payload.get("projects", [])
    if not projects:
        raise SystemExit("No matching project found.")
    project = projects[0]
    project_uuid = project.get("uuid")
    project_ns = (project.get("tenant_meta") or {}).get("namespace") or ns

    step2 = fetch_scan_results.run(
        SimpleNamespace(
            tenant=args.tenant,
            namespace=project_ns,
            project_uuid=project_uuid,
            project_name=None,
            all_projects=False,
            limit=effective_limit,
            scan_window=effective_limit,
            status_filter=args.status_filter,
            output_dir=args.output_dir,
            timestamped=args.timestamped,
        )
    )
    step3 = select_anomalous_scans.run(
        SimpleNamespace(
            input_summary=step2["summary_artifact"],
            output_dir=args.output_dir,
            root_tenant=root,
            project_uuid=project_uuid,
            pair_mode=selected_pair_mode,
            min_delta_findings=args.min_delta_findings,
            min_delta_deps=args.min_delta_deps,
            timestamped=args.timestamped,
        )
    )
    regression_detected = bool(step3.get("regression_detected"))

    if args.regression_only and not regression_detected:
        print("No regression detected in latest scan pair; skipped logs and diff.")
        return 0

    step4 = fetch_scan_logs.run(
        SimpleNamespace(
            tenant=args.tenant,
            namespace=project_ns,
            project_uuid=project_uuid,
            input_pairs=step3["artifact"],
            max_entries=args.max_log_entries,
            output_dir=args.output_dir,
            timestamped=args.timestamped,
        )
    )
    if args.regression_only and not args.emit_diff:
        print(step4["artifact"])
        return 0

    step5 = diff_scans.run(
        SimpleNamespace(
            tenant=args.tenant,
            namespace=project_ns,
            input_pairs=step3["artifact"],
            input_logs_index=step4["artifact"],
            output_dir=args.output_dir,
            timestamped=args.timestamped,
        )
    )
    print(step5["json_artifact"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
