"""Search embedded scan log lines for a regex pattern within an explicit project scope.

Avoids unbounded tenant-wide loops unless ``--all-projects`` is passed explicitly
(and then caps how many projects are scanned).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from endorlabs.client_surface import Client
from endorlabs.workflows.wire_access import as_dict, dict_str, nested_str

from .common import (
    load_json,
    object_to_dict,
    resolve_troubleshooting_output_dir,
    root_tenant,
    write_json,
)
from .scan_error_hits import search_embedded_scan_errors


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
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Directory for generated artifacts (default: "
            ".endorlabs/tasks/<slug>-<YYYY-MM-DD>/troubleshooting/)."
        ),
    )
    parser.add_argument("--timestamped", action="store_true")
    return parser


def _resolve_scope(
    args: argparse.Namespace, projects: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], str]:
    """Return (selected_projects, scope_label)."""
    if args.from_search_artifact:
        data = as_dict(load_json(Path(args.from_search_artifact)))
        plist_raw = data.get("projects")
        plist: list[dict[str, Any]] = []
        if isinstance(plist_raw, list):
            plist.extend(
                cast("dict[str, Any]", item)
                for item in cast("list[Any]", plist_raw)
                if isinstance(item, dict)
            )
        if not plist:
            raise ValueError("search artifact has no projects[]")
        if args.project_uuid:
            sel = [p for p in plist if dict_str(p, "uuid") == args.project_uuid]
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
        selected = [p for p in projects if dict_str(p, "uuid") == args.project_uuid]
        if not selected:
            raise ValueError("project-uuid not found under tenant listing")
        return selected, "project_uuid"

    if args.project_name:
        selected = [
            p
            for p in projects
            if args.project_name.lower() in nested_str(p, "meta", "name").lower()
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
    client = Client(tenant=ns)
    if not args.from_search_artifact:
        traverse = "." not in ns
        projects = [
            object_to_dict(p)
            for p in client.Project.list(namespace=ns, traverse=traverse)
        ]
    else:
        projects = []

    selected_projects, scope_label = _resolve_scope(args, projects)
    evidence = search_embedded_scan_errors(
        client,
        projects=selected_projects,
        error_pattern=args.error_pattern,
        query_namespace=ns,
        limit=args.limit,
        max_workers=args.max_workers,
    )
    hits = evidence.hits

    scope_uuid = args.project_uuid or dict_str(selected_projects[0], "uuid") or "scoped"
    output_dir = resolve_troubleshooting_output_dir(
        args.tenant or args.namespace, args.output_dir
    )
    payload: dict[str, Any] = {
        "root_tenant": root,
        "query_namespace": ns,
        "scope_mode": scope_label,
        "error_pattern": args.error_pattern,
        "project_count": len(selected_projects),
        "hit_count": len(hits),
        "hits": hits,
    }
    artifact = write_json(
        output_dir=output_dir,
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
