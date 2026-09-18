"""CLI: AI-SAST function_summary → Call Graph bridge."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.context.paths import task_activity_dir
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.aisast_callgraph.run import run_aisast_callgraph_bridge
from endorlabs.workflows.aisast_callgraph.seeds import ENTRY_POINT_QUERY
from endorlabs.workflows.projects.discovery import resolve_project_candidate

LOGGER = get_resource_logger(__name__)


def parse_aisast_callgraph_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse ``endor-aisast-callgraph`` arguments."""
    p = argparse.ArgumentParser(
        description=(
            "Precheck MAIN AI-SAST index + Call Graph, then map function_summary "
            "seeds to CallGraphData symbols. Optional safe BFS via --path-to "
            "and/or Finding-derived package tokens (--vuln / --finding-package)."
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
        "--path-to",
        action="append",
        default=[],
        help=(
            "Optional repeatable CG URI substring targets for BFS walk "
            "(package/symbol fragments — not GHSA/CVE ids)."
        ),
    )
    p.add_argument(
        "--vuln",
        default="",
        help=(
            "Optional GHSA/CVE/Finding name filter. Resolves Finding package "
            "coordinate → CG path-to token (advisory id is never a URI pattern)."
        ),
    )
    p.add_argument(
        "--finding-package",
        default="",
        help=(
            "Optional substring on Finding target_dependency_package_name "
            "to derive CG path-to (e.g. jsonwebtoken)."
        ),
    )
    p.add_argument(
        "--path-to-symbol",
        default="",
        help="Optional AND-ed symbol fragment with package path-to (e.g. sign).",
    )
    p.add_argument(
        "--max-depth",
        type=int,
        default=6,
        help="BFS max depth when walking (default: 6, capped at 12).",
    )
    p.add_argument(
        "--max-paths",
        type=int,
        default=5,
        help="Max BFS paths retained per seed (default: 5, capped at 20).",
    )
    p.add_argument(
        "--max-seeds",
        type=int,
        default=40,
        help="Cap AI-SAST seed rows (default: 40).",
    )
    p.add_argument(
        "--query",
        default=ENTRY_POINT_QUERY,
        help="Natural-language vector query for function_summary seeds.",
    )
    p.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Max pages for RepositoryVersion / PackageVersion lists.",
    )
    p.add_argument(
        "--out",
        default="",
        help=(
            "Output JSON path. Default: "
            ".endorlabs/tasks/<slug>-<date>/aisast-callgraph/bridge.json"
        ),
    )
    return p.parse_args(argv)


def _default_out_path(namespace: str) -> Path:
    out_dir = task_activity_dir(namespace, "aisast-callgraph")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / "bridge.json"


def run_aisast_callgraph_main(argv: list[str] | None = None) -> int:
    """CLI entry for AI-SAST → Call Graph bridge."""
    args = parse_aisast_callgraph_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ns = (args.namespace or args.tenant).strip()

    client = endorlabs.Client(tenant=args.tenant)
    try:
        proj = resolve_project_candidate(client, args.project, namespace=ns)
        project_ns = (
            proj.tenant_meta.namespace
            if proj.tenant_meta and proj.tenant_meta.namespace
            else ns
        )
        result = run_aisast_callgraph_bridge(
            client,
            proj,
            tenant=args.tenant,
            namespace=project_ns,
            path_to=list(args.path_to or []),
            vuln_id=(args.vuln or "").strip() or None,
            finding_package=(args.finding_package or "").strip() or None,
            path_to_symbol=(args.path_to_symbol or "").strip() or None,
            max_depth=args.max_depth,
            max_paths=args.max_paths,
            max_seeds=args.max_seeds,
            max_pages=args.max_pages,
            query=args.query,
        )
        payload: dict[str, Any] = result.as_dict()
    finally:
        client.close()

    text = json.dumps(payload, indent=2, ensure_ascii=False)
    out_path = Path(args.out).resolve() if args.out else _default_out_path(ns)
    safe_write_text(out_path.parent, out_path, text)
    LOGGER.info("Wrote bridge output: %s", out_path)
    payload["artifact"] = str(out_path)
    # Re-write with artifact path for discoverability
    safe_write_text(
        out_path.parent,
        out_path,
        json.dumps(payload, indent=2, ensure_ascii=False),
    )
    if not args.out:
        sys.stdout.write(text)
        sys.stdout.write("\n")
        sys.stdout.write(f"artifact: {out_path}\n")
    return 0 if payload.get("status") == "success" else 1


def main() -> int:
    """``endor-aisast-callgraph`` entrypoint."""
    return run_aisast_callgraph_main()


if __name__ == "__main__":
    raise SystemExit(main())
