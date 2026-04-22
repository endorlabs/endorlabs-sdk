"""Search scan results and logs for an error pattern."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

try:
    from scripts.troubleshooting_scans.common import (
        build_api_client,
        list_projects,
        list_scan_results_for_project,
        root_tenant,
        write_json,
    )
except ModuleNotFoundError:
    from common import (
        build_api_client,
        list_projects,
        list_scan_results_for_project,
        root_tenant,
        write_json,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search scan error signatures")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--namespace")
    parser.add_argument("--project-uuid")
    parser.add_argument("--project-name")
    parser.add_argument("--all-projects", action="store_true")
    parser.add_argument("--error-pattern", required=True)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--context-lines", type=int, default=1)
    parser.add_argument("--output-dir", default=".tmp")
    parser.add_argument("--timestamped", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    ns = args.namespace or args.tenant
    root = root_tenant(ns)
    pattern = re.compile(args.error_pattern, re.IGNORECASE)
    api = build_api_client()

    projects = list_projects(api, ns)
    if args.all_projects:
        selected_projects = projects
    elif args.project_uuid:
        selected_projects = [p for p in projects if p.get("uuid") == args.project_uuid]
    elif args.project_name:
        selected_projects = [
            p
            for p in projects
            if args.project_name.lower() in str((p.get("meta") or {}).get("name", "")).lower()
        ]
    else:
        raise ValueError("Provide target project selector or --all-projects")

    hits: list[dict[str, Any]] = []
    for project in selected_projects:
        project_uuid = project.get("uuid")
        project_ns = (project.get("tenant_meta") or {}).get("namespace") or ns
        if not project_uuid:
            continue
        scan_results = list_scan_results_for_project(
            api, namespace=project_ns, project_uuid=project_uuid, limit=args.limit
        )
        for scan_result in scan_results:
            scan_uuid = scan_result.get("uuid")
            scan_logs = (scan_result.get("spec") or {}).get("logs") or []
            for line in scan_logs:
                if pattern.search(str(line)):
                    hits.append(
                        {
                            "project_uuid": project_uuid,
                            "project_namespace": project_ns,
                            "scan_result_uuid": scan_uuid,
                            "status": (scan_result.get("spec") or {}).get("status"),
                            "match_line": str(line),
                        }
                    )

    scope_uuid = args.project_uuid or "tenant-scope"
    payload = {
        "root_tenant": root,
        "query_namespace": ns,
        "error_pattern": args.error_pattern,
        "project_count": len(selected_projects),
        "hit_count": len(hits),
        "hits": hits,
    }
    artifact = write_json(
        output_dir=Path(args.output_dir),
        root_tenant_name=root,
        object_kind="scan_error_hits",
        object_uuid=scope_uuid,
        purpose="results",
        payload=payload,
        timestamped=args.timestamped,
    )
    payload["artifact"] = str(artifact)
    return payload


def main() -> int:
    args = build_parser().parse_args()
    result = run(args)
    print(result["artifact"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
