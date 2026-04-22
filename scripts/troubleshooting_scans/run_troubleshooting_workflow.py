"""Run the full troubleshooting-scans workflow end-to-end."""

from __future__ import annotations

import argparse
from types import SimpleNamespace

try:
    from scripts.troubleshooting_scans import (
        diff_scans,
        fetch_scan_logs,
        fetch_scan_results,
        resolve_projects,
        select_anomalous_scans,
    )
    from scripts.troubleshooting_scans.common import load_json, root_tenant
except ModuleNotFoundError:
    import diff_scans
    import fetch_scan_logs
    import fetch_scan_results
    import resolve_projects
    import select_anomalous_scans
    from common import load_json, root_tenant


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run full troubleshooting workflow")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--namespace")
    parser.add_argument("--project-uuid")
    parser.add_argument("--project-name")
    parser.add_argument("--project-url")
    parser.add_argument("--project-name-regex")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--status-filter")
    parser.add_argument("--pair-mode", choices=["adjacent", "best-anomaly"], default="best-anomaly")
    parser.add_argument("--min-delta-findings", type=int, default=10)
    parser.add_argument("--min-delta-deps", type=int, default=50)
    parser.add_argument("--max-log-entries", type=int, default=500)
    parser.add_argument("--output-dir", default=".tmp")
    parser.add_argument("--timestamped", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    ns = args.namespace or args.tenant
    root = root_tenant(ns)

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
            limit=args.limit,
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
            pair_mode=args.pair_mode,
            min_delta_findings=args.min_delta_findings,
            min_delta_deps=args.min_delta_deps,
            timestamped=args.timestamped,
        )
    )
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
