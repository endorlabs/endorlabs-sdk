"""Fetch scan results for one project or tenant-wide."""

from __future__ import annotations

import argparse
from typing import Any

from endorlabs.client_surface import Client
from endorlabs.workflows.wire_access import dict_str, nested_str

from .common import (
    object_to_dict,
    resolve_troubleshooting_output_dir,
    root_tenant,
    write_json,
)
from .scan_results_evidence import acquire_scan_results, list_scan_result_dicts

# Compat: CLI/tests may import the old private helper name.
_list_scan_dicts = list_scan_result_dicts


def build_parser() -> argparse.ArgumentParser:
    """Build argparse parser for this workflow CLI."""
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
    _ = parser.add_argument(
        "--max-workers",
        type=int,
        default=8,
        help="Parallel workers when fetching multiple projects. Default: 8",
    )
    _ = parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Directory for generated artifacts (default: "
            ".endorlabs/tasks/<slug>-<YYYY-MM-DD>/troubleshooting/)."
        ),
    )
    _ = parser.add_argument("--timestamped", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Execute workflow from parsed CLI args."""
    ns = args.namespace or args.tenant
    client = Client(tenant=ns)
    root = root_tenant(ns)
    output_dir = resolve_troubleshooting_output_dir(
        args.tenant or args.namespace, args.output_dir
    )
    effective_limit = args.scan_window or args.limit

    traverse = "." not in ns
    project_rows = client.Project.list(namespace=ns, traverse=traverse)
    projects = [object_to_dict(p) for p in project_rows]
    selected_projects = projects
    if not args.all_projects:
        if args.project_uuid:
            selected_projects = [
                p for p in projects if dict_str(p, "uuid") == args.project_uuid
            ]
        elif args.project_name:
            selected_projects = [
                p
                for p in projects
                if args.project_name.lower() in nested_str(p, "meta", "name").lower()
            ]
        else:
            raise ValueError(
                "Provide --project-uuid or --project-name unless --all-projects"
            )

    evidence = acquire_scan_results(
        client,
        query_namespace=ns,
        projects=selected_projects,
        limit=effective_limit,
        status_filter=args.status_filter,
        max_workers=args.max_workers,
    )
    all_results = evidence.scan_results
    summaries = evidence.summaries

    primary_uuid = (
        args.project_uuid
        or (dict_str(selected_projects[0], "uuid") if selected_projects else None)
        or "tenant-scope"
    )

    raw_payload: dict[str, Any] = {
        "root_tenant": root,
        "query_namespace": ns,
        "project_count": len(selected_projects),
        "scan_result_count": len(all_results),
        "scan_results": all_results,
    }
    summary_payload: dict[str, Any] = {
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
    """Run the module CLI and return exit code."""
    args = build_parser().parse_args()
    result = run(args)
    print(result["summary_artifact"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
