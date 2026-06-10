#!/usr/bin/env python3
"""Build a project-to-project dependency relationship graph in a namespace."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import endorlabs
from endorlabs.context.paths import workflow_projects_root
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.estate.analyze.project_map.run import (
    run_project_relationship_map,
)

LOGGER = get_resource_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Build argparse parser for this workflow CLI."""
    p = argparse.ArgumentParser(
        description=(
            "Namespace-wide project relationship graph "
            "(PackageVersion + DependencyMetadata)."
        )
    )
    p.add_argument(
        "--tenant", required=True, help="Client tenant (auth) as for endorlabs.Client."
    )
    p.add_argument(
        "--namespace",
        required=True,
        help="Root namespace to traverse (e.g. tenant or tenant.child).",
    )
    p.add_argument(
        "--include-public",
        action="store_true",
        help="Keep dependency rows marked public (default: skip).",
    )
    p.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Max hop count for indirect project paths. Default: 3",
    )
    p.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Max pages for Project/PackageVersion lists (0 = unlimited).",
    )
    p.add_argument(
        "--page-size",
        type=int,
        default=500,
        help="List page size. Default: 500",
    )
    p.add_argument(
        "--dep-metadata-max-pages",
        type=int,
        default=0,
        help="Max pages per project for DependencyMetadata (0 = unlimited).",
    )
    p.add_argument(
        "--max-workers",
        type=int,
        default=16,
        help="Parallel workers for per-project DependencyMetadata collect. Default: 16",
    )
    p.add_argument(
        "--output-dir",
        default=str(workflow_projects_root()),
        help="Output directory. Default: .endorlabs-context/workspace/projects",
    )
    p.add_argument(
        "--focus-producer-project-uuid",
        default="",
        help=(
            "Optional 24-hex producer project UUID. Restrict producer PackageVersion "
            "index to this project and return only consumer→producer edges (and paths) "
            "where this project is the producer — e.g. breaking-change blast radius."
        ),
    )
    return p.parse_args()


def main() -> int:
    """Run the module CLI and return exit code."""
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    out_dir = Path(args.output_dir)

    client = endorlabs.Client(tenant=args.tenant)
    try:
        run_project_relationship_map(
            client,
            namespace=args.namespace,
            output_dir=out_dir,
            include_public=bool(args.include_public),
            max_depth=args.max_depth,
            max_pages=args.max_pages,
            page_size=args.page_size,
            dep_metadata_max_pages=args.dep_metadata_max_pages,
            max_workers=args.max_workers,
            focus_producer_project_uuid=(args.focus_producer_project_uuid or "").strip()
            or None,
        )
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
