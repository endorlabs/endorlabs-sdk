"""Fetch scan results for one project or tenant-wide."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .common import (
    build_api_client,
    list_projects,
    list_scan_results_for_project,
    root_tenant,
    scan_result_metrics,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch scan result window")
    _ = parser.add_argument("--tenant", required=True)
    _ = parser.add_argument("--project-uuid")
    _ = parser.add_argument("--project-name")
    _ = parser.add_argument("--namespace")
    _ = parser.add_argument("--all-projects", action="store_true")
    _ = parser.add_argument("--limit", type=int, default=25)
    _ = parser.add_argument(
        "--scan-window",
        type=int,
        help="Optional alias for --limit to emphasize bounded scan windows.",
    )
    _ = parser.add_argument("--status-filter")
    _ = parser.add_argument("--output-dir", default=".tmp")
    _ = parser.add_argument("--timestamped", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    api = build_api_client()
    ns = args.namespace or args.tenant
    root = root_tenant(ns)
    output_dir = Path(args.output_dir)
    effective_limit = args.scan_window or args.limit

    projects = list_projects(api, ns)
    selected_projects = projects
    if not args.all_projects:
        if args.project_uuid:
            selected_projects = [
                p for p in projects if p.get("uuid") == args.project_uuid
            ]
        elif args.project_name:
            selected_projects = [
                p
                for p in projects
                if args.project_name.lower()
                in str((p.get("meta") or {}).get("name", "")).lower()
            ]
        else:
            raise ValueError(
                "Provide --project-uuid or --project-name unless --all-projects"
            )

    all_results: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for project in selected_projects:
        project_uuid = project.get("uuid")
        project_ns = (project.get("tenant_meta") or {}).get("namespace") or ns
        if not project_uuid:
            continue
        results = list_scan_results_for_project(
            api,
            namespace=project_ns,
            project_uuid=project_uuid,
            limit=effective_limit,
            status_filter=args.status_filter,
        )
        all_results.extend(results)
        summaries.extend(scan_result_metrics(item) for item in results)

    primary_uuid = (
        args.project_uuid
        or (selected_projects[0].get("uuid") if selected_projects else None)
        or "tenant-scope"
    )

    raw_payload = {
        "root_tenant": root,
        "query_namespace": ns,
        "project_count": len(selected_projects),
        "scan_result_count": len(all_results),
        "scan_results": all_results,
    }
    summary_payload = {
        "root_tenant": root,
        "query_namespace": ns,
        "project_count": len(selected_projects),
        "scan_result_count": len(summaries),
        "scan_results_summary": summaries,
    }
    raw_artifact = write_json(
        output_dir=output_dir,
        root_tenant_name=root,
        object_kind="scan_results",
        object_uuid=primary_uuid,
        purpose="raw",
        payload=raw_payload,
        timestamped=args.timestamped,
    )
    summary_artifact = write_json(
        output_dir=output_dir,
        root_tenant_name=root,
        object_kind="scan_results",
        object_uuid=primary_uuid,
        purpose="summary",
        payload=summary_payload,
        timestamped=args.timestamped,
    )
    return {
        "raw_artifact": str(raw_artifact),
        "summary_artifact": str(summary_artifact),
        "project_count": len(selected_projects),
        "scan_result_count": len(summaries),
    }


def main() -> int:
    args = build_parser().parse_args()
    result = run(args)
    print(result["summary_artifact"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
