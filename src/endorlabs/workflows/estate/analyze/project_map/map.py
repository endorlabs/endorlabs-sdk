#!/usr/bin/env python3
"""Build a project-to-project dependency relationship graph in a namespace."""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs import F
from endorlabs.context.paths import workflow_projects_root
from endorlabs.tools.dependency_explorer import write_json
from endorlabs.workflows.estate.analyze.project_map.core import (
    SupportingPackage,
    add_producer_indices,
    aggregate_project_edges,
    indirect_paths_bfs,
    row_to_supporting_tuples,
)
from endorlabs.workflows.estate.collect.bounds import (
    format_progress,
    is_list_truncated,
    resolve_max_pages,
)
from endorlabs.workflows.estate.collect.shards import (
    ParentShard,
    parallel_map_shards,
    project_model_to_shard,
)

LOGGER = logging.getLogger(__name__)


def _object_to_spec_dict(d: Any) -> dict[str, Any]:
    if hasattr(d, "model_dump"):
        raw = d.model_dump(mode="json", warnings=False)
    else:
        raw: Any = d
    if not isinstance(raw, dict):
        return {}
    s = raw.get("spec")
    if isinstance(s, dict):
        return s
    return raw


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
    return p.parse_args()


def main() -> int:
    """Run the module CLI and return exit code."""
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = endorlabs.Client(tenant=args.tenant)
    try:
        list_max_pages = resolve_max_pages(args.max_pages)
        projects = client.Project.list(
            namespace=args.namespace,
            traverse=True,
            max_pages=list_max_pages,
            page_size=args.page_size,
        )
        if is_list_truncated(
            len(projects), max_pages=list_max_pages, page_size=args.page_size
        ):
            LOGGER.warning(
                "Project list may be truncated at %d rows; "
                "use --max-pages 0 for full estate",
                len(projects),
            )
        project_set = {p.uuid for p in projects if p.uuid}
        projects_json = [
            {
                "uuid": p.uuid,
                "name": (p.meta.name if p.meta and p.meta.name else p.uuid),
                "namespace": (
                    p.tenant_meta.namespace
                    if p.tenant_meta and p.tenant_meta.namespace
                    else args.namespace
                ),
            }
            for p in projects
        ]
        pvs = client.PackageVersion.list(
            namespace=args.namespace,
            traverse=True,
            max_pages=list_max_pages,
            page_size=args.page_size,
        )
        if is_list_truncated(
            len(pvs), max_pages=list_max_pages, page_size=args.page_size
        ):
            LOGGER.warning(
                "PackageVersion list may be truncated at %d rows; use --max-pages 0",
                len(pvs),
            )
        produced_by: dict[tuple[str, str], set[str]] = {}
        produced_name: dict[str, set[str]] = {}
        n_pv = 0
        for pv in pvs:
            puid = getattr(pv.spec, "project_uuid", None) if pv.spec else None
            if not puid or puid not in project_set:
                continue
            n_pv += 1
            mname = pv.meta.name if pv.meta and pv.meta.name else ""
            add_producer_indices(mname, str(puid), produced_by, produced_name)
        all_support: list[tuple[str, str, SupportingPackage]] = []
        n_dep = 0
        dm_max_pages = resolve_max_pages(args.dep_metadata_max_pages)
        dep_shards = [
            project_model_to_shard(p, args.namespace) for p in projects if p.uuid
        ]

        def _fetch_dep_metadata(shard: ParentShard) -> tuple[list[Any], int]:
            drows: list[Any] = []
            try:
                drows = client.DependencyMetadata.list(
                    filter=(F("spec.importer_data.project_uuid") == shard.key),
                    namespace=shard.namespace,
                    max_pages=dm_max_pages,
                    page_size=args.page_size,
                )
                if is_list_truncated(
                    len(drows),
                    max_pages=dm_max_pages,
                    page_size=args.page_size,
                ):
                    LOGGER.warning(
                        "DependencyMetadata truncated for project %s (%d rows)",
                        shard.key,
                        len(drows),
                    )
            except (ValueError, TypeError, RuntimeError) as e:
                LOGGER.debug("dep metadata for project %s: %s", shard.key, e)
                drows = []
            support: list[tuple[str, str, SupportingPackage]] = []
            for d in drows or []:
                sp = _object_to_spec_dict(d)
                support.extend(
                    row_to_supporting_tuples(
                        sp,
                        project_set,
                        include_public=bool(args.include_public),
                        produced_by=produced_by,
                        produced_name_only=produced_name,
                    )
                )
            return support, len(drows or [])

        dep_rows_total = 0

        def _on_dep_progress(completed: int, total: int) -> None:
            LOGGER.info(
                "%s",
                format_progress("DependencyMetadata projects", completed, total),
            )

        for support, row_count in parallel_map_shards(
            dep_shards,
            _fetch_dep_metadata,
            max_workers=args.max_workers,
            progress_label="DependencyMetadata projects",
            progress_every=50,
            on_progress=_on_dep_progress,
        ):
            all_support.extend(support)
            dep_rows_total += row_count
        n_dep = dep_rows_total
        edges = aggregate_project_edges(all_support)
        paths = indirect_paths_bfs(
            [p["uuid"] for p in projects_json],
            edges,
            args.max_depth,
        )
        tier_counts: dict[str, int] = {
            "tier_a_exact": sum(
                1 for e in edges if e.get("evidence_tier") == "tier_a_exact"
            ),
            "tier_b_name_only": sum(
                1 for e in edges if e.get("evidence_tier") == "tier_b_name_only"
            ),
        }
        ts = datetime.now(UTC).isoformat() + "Z"
        gjs = {
            "namespace": args.namespace,
            "generated_at": ts,
            "projects": projects_json,
            "edges": edges,
        }
        pjs = {
            "namespace": args.namespace,
            "max_depth": args.max_depth,
            "paths": paths,
        }
        sjs = {
            "namespace": args.namespace,
            "project_count": len(projects_json),
            "package_version_count": n_pv,
            "dependency_row_count": n_dep,
            "direct_project_edge_count": len(edges),
            "indirect_path_count": len(paths),
            "tier_counts": tier_counts,
        }
        write_json(
            str(out_dir / "project_relationship_graph.json"), gjs, base_dir=out_dir
        )
        write_json(
            str(out_dir / "project_relationship_paths.json"), pjs, base_dir=out_dir
        )
        write_json(
            str(out_dir / "project_relationship_stats.json"), sjs, base_dir=out_dir
        )
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
