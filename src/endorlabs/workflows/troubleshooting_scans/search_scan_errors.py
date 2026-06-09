"""Search embedded scan log lines for a regex pattern within an explicit project scope.

Avoids unbounded tenant-wide loops unless ``--all-projects`` is passed explicitly
(and then caps how many projects are scanned).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from endorlabs.workflows.estate.collect.shards import ParentShard

from .common import (
    build_api_client,
    default_troubleshooting_output_dir,
    list_projects,
    list_scan_results_for_project,
    load_json,
    parallel_collect_for_projects,
    root_tenant,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    """Build argparse parser for this workflow CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Search embedded spec.logs lines for a regex. "
            "Requires explicit scope: project selector, --from-search-artifact, "
            "or --all-projects."
        )
    )
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--namespace")
    parser.add_argument("--project-uuid")
    parser.add_argument("--project-name")
    parser.add_argument(
        "--from-search-artifact",
        default=None,
        help=(
            "JSON from search_projects.py (uses projects[0].uuid unless --project-uuid)"
        ),
    )
    parser.add_argument(
        "--all-projects",
        action="store_true",
        help="Search all projects under namespace (expensive; see --max-projects)",
    )
    parser.add_argument(
        "--max-projects",
        type=int,
        default=25,
        help="Cap when using --all-projects (default 25)",
    )
    parser.add_argument("--error-pattern", required=True)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument(
        "--max-workers",
        type=int,
        default=8,
        help="Parallel workers when searching multiple projects. Default: 8",
    )
    parser.add_argument(
        "--context-lines",
        type=int,
        default=1,
        help="Reserved for future use (embedded logs are single-line JSON strings)",
    )
    parser.add_argument("--output-dir", default=default_troubleshooting_output_dir())
    parser.add_argument("--timestamped", action="store_true")
    return parser


def _resolve_scope(
    args: argparse.Namespace, projects: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], str]:
    """Return (selected_projects, scope_label)."""
    if args.from_search_artifact:
        data = load_json(Path(args.from_search_artifact))
        plist = data.get("projects") or []
        if not plist:
            raise ValueError("search artifact has no projects[]")
        if args.project_uuid:
            sel = [p for p in plist if p.get("uuid") == args.project_uuid]
            if not sel:
                raise ValueError("--project-uuid not found in search artifact")
            return sel, "artifact"
        return [plist[0]], "artifact"

    if args.all_projects:
        if len(projects) > args.max_projects:
            projects = projects[: args.max_projects]
        print(
            json.dumps(
                {
                    "warning": "all_projects_capped",
                    "max_projects": args.max_projects,
                    "scanned": len(projects),
                }
            ),
            file=sys.stderr,
        )
        return projects, "all_projects_capped"

    if args.project_uuid:
        selected = [p for p in projects if p.get("uuid") == args.project_uuid]
        if not selected:
            raise ValueError("project-uuid not found under tenant listing")
        return selected, "project_uuid"

    if args.project_name:
        selected = [
            p
            for p in projects
            if args.project_name.lower()
            in str((p.get("meta") or {}).get("name", "")).lower()
        ]
        if not selected:
            raise ValueError("No project matched --project-name")
        return selected, "project_name"

    raise ValueError(
        "Provide --project-uuid, --project-name, --from-search-artifact, "
        "or --all-projects"
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Execute workflow from parsed CLI args."""
    _ = args.context_lines
    ns = args.namespace or args.tenant
    root = root_tenant(ns)
    pattern = re.compile(args.error_pattern, re.IGNORECASE)
    api = build_api_client()
    projects = list_projects(api, ns) if not args.from_search_artifact else []

    selected_projects, scope_label = _resolve_scope(args, projects)

    hits: list[dict[str, Any]] = []

    def _search_project(shard: ParentShard) -> list[dict[str, Any]]:
        project_hits: list[dict[str, Any]] = []
        scan_results = list_scan_results_for_project(
            api,
            namespace=shard.namespace,
            project_uuid=shard.key,
            limit=args.limit,
        )
        for scan_result in scan_results:
            scan_uuid = scan_result.get("uuid")
            scan_logs = (scan_result.get("spec") or {}).get("logs") or []
            project_hits.extend(
                {
                    "project_uuid": shard.key,
                    "project_namespace": shard.namespace,
                    "scan_result_uuid": scan_uuid,
                    "status": (scan_result.get("spec") or {}).get("status"),
                    "match_line": str(line),
                }
                for line in scan_logs
                if pattern.search(str(line))
            )
        return project_hits

    if len(selected_projects) > 1:
        hits = parallel_collect_for_projects(
            selected_projects,
            _search_project,
            max_workers=args.max_workers,
            fallback_ns=ns,
            progress_label="scan error search projects",
        )
    else:
        for project in selected_projects:
            project_uuid = project.get("uuid")
            project_ns = (project.get("tenant_meta") or {}).get("namespace") or ns
            if not project_uuid:
                continue
            shard = ParentShard(key=str(project_uuid), namespace=str(project_ns))
            hits.extend(_search_project(shard))

    scope_uuid = args.project_uuid or selected_projects[0].get("uuid") or "scoped"
    payload = {
        "root_tenant": root,
        "query_namespace": ns,
        "scope_mode": scope_label,
        "error_pattern": args.error_pattern,
        "project_count": len(selected_projects),
        "hit_count": len(hits),
        "hits": hits,
    }
    artifact = write_json(
        output_dir=Path(args.output_dir),
        root_tenant_name=root,
        object_kind="scan_error_hits",
        object_uuid=str(scope_uuid),
        purpose="results",
        payload=payload,
        timestamped=args.timestamped,
    )
    payload["artifact"] = str(artifact)
    return payload


def main() -> int:
    """Run the module CLI and return exit code."""
    args = build_parser().parse_args()
    try:
        result = run(args)
    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1
    print(result["artifact"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
