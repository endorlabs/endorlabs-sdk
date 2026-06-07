"""Resolve projects by UUID/name/URL within a tenant namespace."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .common import (
    build_api_client,
    list_projects,
    match_projects,
    root_tenant,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    """Build argparse parser for this workflow CLI."""
    parser = argparse.ArgumentParser(description="Resolve project candidates")
    parser.add_argument("--tenant", required=True, help="Namespace root/tenant")
    parser.add_argument("--namespace", help="Namespace to query (defaults to tenant)")
    parser.add_argument("--project-uuid")
    parser.add_argument("--project-name")
    parser.add_argument("--project-url")
    parser.add_argument("--project-name-regex")
    parser.add_argument("--output-dir", default=".tmp")
    parser.add_argument("--timestamped", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Execute workflow from parsed CLI args."""
    ns = args.namespace or args.tenant
    api = build_api_client()
    projects = list_projects(api, ns)
    selected = match_projects(
        projects,
        project_uuid=args.project_uuid,
        project_name=args.project_name,
        project_url=args.project_url,
        project_name_regex=args.project_name_regex,
    )
    root = root_tenant(ns)
    output_dir = Path(args.output_dir)

    object_uuid = selected[0].get("uuid", "unknown") if selected else "no-match"

    payload = {
        "root_tenant": root,
        "query_namespace": ns,
        "total_projects": len(projects),
        "selected_count": len(selected),
        "filters": {
            "project_uuid": args.project_uuid,
            "project_name": args.project_name,
            "project_url": args.project_url,
            "project_name_regex": args.project_name_regex,
        },
        "projects": selected,
    }
    artifact = write_json(
        output_dir=output_dir,
        root_tenant_name=root,
        object_kind="project",
        object_uuid=object_uuid,
        purpose="project_candidates",
        payload=payload,
        timestamped=args.timestamped,
    )
    payload["artifact"] = str(artifact)
    return payload


def main() -> int:
    """Run the module CLI and return exit code."""
    args = build_parser().parse_args()
    result = run(args)
    print(result["artifact"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
