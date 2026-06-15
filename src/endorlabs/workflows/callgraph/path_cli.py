"""Live API CLI: resolve project, decode call graph, run path search."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.callgraph.path import find_call_graph_path
from endorlabs.workflows.callgraph.resolve import resolve_package_version_with_callgraph
from endorlabs.workflows.projects.discovery import resolve_project_candidate

LOGGER = get_resource_logger(__name__)


def parse_path_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse ``endor-callgraph-path`` arguments."""
    p = argparse.ArgumentParser(
        description=(
            "Resolve a project package version, decode its call graph, "
            "and search for a multi-hop path between symbols."
        )
    )
    p.add_argument("--tenant", required=True, help="Client tenant (auth context).")
    p.add_argument(
        "--namespace",
        default="",
        help="Namespace for project resolution (default: --tenant).",
    )
    p.add_argument(
        "--project",
        required=True,
        help="Project UUID or exact project name.",
    )
    p.add_argument(
        "--path-from",
        action="append",
        default=[],
        required=True,
        help="Repeatable URI substring patterns for path start.",
    )
    p.add_argument(
        "--path-to",
        action="append",
        default=[],
        required=True,
        help="Repeatable URI substring patterns for path end.",
    )
    p.add_argument(
        "--max-depth",
        type=int,
        default=6,
        help="Maximum BFS depth (default: 6).",
    )
    p.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Max pages for PackageVersion.list_by_project.",
    )
    p.add_argument(
        "--page-size",
        type=int,
        default=200,
        help="Page size for PackageVersion.list_by_project.",
    )
    p.add_argument(
        "--max-attempts",
        type=int,
        default=0,
        help="Max PV decode attempts (0 = all listed PVs).",
    )
    p.add_argument(
        "--out",
        default="",
        help="Optional output JSON path (stdout if omitted).",
    )
    return p.parse_args(argv)


def run_path_search(
    client: Any,
    *,
    namespace: str,
    project: Any,
    from_patterns: list[str],
    to_patterns: list[str],
    max_depth: int,
    max_pages: int,
    page_size: int,
    max_attempts: int | None,
) -> dict[str, Any]:
    """Decode first call-graph-capable PV and run path search."""
    inventory: dict[str, Any] = {}
    resolved = resolve_package_version_with_callgraph(
        client,
        project,
        namespace=namespace,
        max_pages=max_pages,
        page_size=page_size,
        max_attempts=max_attempts,
        inventory_out=inventory,
    )
    if resolved is None:
        return {
            "status": "error",
            "message": inventory.get(
                "message",
                "No decodable CallGraphData found for call_graph_available "
                "package versions.",
            ),
            "callgraph_pv_inventory": inventory,
            "from_pattern": from_patterns,
            "to_pattern": to_patterns,
            "path_found": False,
            "paths": [],
        }

    pv, decoded = resolved
    path_result = find_call_graph_path(
        decoded.callables,
        decoded.edges,
        from_patterns=from_patterns,
        to_patterns=to_patterns,
        max_depth=max_depth,
    )
    pv_name = pv.meta.name if pv.meta and pv.meta.name else pv.uuid
    return {
        "status": "success",
        "pv_uuid": pv.uuid,
        "pv_name": pv_name,
        **path_result,
    }


def run_path_main(argv: list[str] | None = None) -> int:
    """CLI entry for live path search."""
    args = parse_path_cli_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ns = (args.namespace or args.tenant).strip()
    max_attempts = args.max_attempts if args.max_attempts > 0 else None

    client = endorlabs.Client(tenant=args.tenant)
    try:
        proj = resolve_project_candidate(client, args.project, namespace=ns)
        project_ns = (
            proj.tenant_meta.namespace
            if proj.tenant_meta and proj.tenant_meta.namespace
            else ns
        )
        payload = run_path_search(
            client,
            namespace=project_ns,
            project=proj,
            from_patterns=args.path_from,
            to_patterns=args.path_to,
            max_depth=args.max_depth,
            max_pages=args.max_pages,
            page_size=args.page_size,
            max_attempts=max_attempts,
        )
    finally:
        client.close()

    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.out:
        out_path = Path(args.out).resolve()
        safe_write_text(out_path.parent, out_path, text)
        LOGGER.info("Wrote path search output: %s", out_path)
    else:
        sys.stdout.write(text)
        sys.stdout.write("\n")
    return 0 if payload.get("status") == "success" else 1


def main() -> int:
    """``endor-callgraph-path`` entrypoint."""
    return run_path_main()


if __name__ == "__main__":
    raise SystemExit(main())
