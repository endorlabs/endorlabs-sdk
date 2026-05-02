#!/usr/bin/env python3
"""Build a project-to-project dependency relationship graph in a namespace."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import endorlabs
from endorlabs import F

from scripts.relationship_mapping.relationship_map_core import (
    add_producer_indices,
    aggregate_project_edges,
    indirect_paths_bfs,
    row_to_supporting_tuples,
)
from endorlabs.tools.dependency_explorer import write_json

LOGGER = logging.getLogger(__name__)


def _object_to_spec_dict(d: Any) -> dict[str, Any]:
    if hasattr(d, "model_dump"):
        raw = d.model_dump(mode="json", warnings=False)
    else:
        raw = d  # type: ignore[assignment]
    if not isinstance(raw, dict):
        return {}
    s = raw.get("spec")
    if isinstance(s, dict):
        return s
    return raw


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Namespace-wide project relationship graph (PackageVersion + DependencyMetadata)."
    )
    p.add_argument(
        "--tenant", required=True, help="Client tenant (auth) as for endorlabs.Client."
    )
    p.add_argument(
        "--namespace", required=True, help="Root namespace to traverse (e.g. tenant or tenant.child)."
    )
    p.add_argument(
        "--include-public", action="store_true", help="Keep dependency rows marked public (default: skip)."
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
        default=25,
        help="Max pages for Project/PackageVersion lists. Default: 25",
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
        default=5,
        help="Max pages per project for DependencyMetadata list. Default: 5",
    )
    p.add_argument(
        "--output-dir",
        default=".tmp",
        help="Output directory. Default: .tmp",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = endorlabs.Client(tenant=args.tenant)
    try:
        projects = client.Project.list(
            namespace=args.namespace,
            traverse=True,
            max_pages=args.max_pages,
            page_size=args.page_size,
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
            max_pages=args.max_pages,
            page_size=args.page_size,
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
            add_producer_indices(
                mname, str(puid), produced_by, produced_name
            )
        all_support: list = []
        n_dep = 0
        for p in projects:
            if not p.uuid:
                continue
            drows: list = []
            try:
                drows = client.DependencyMetadata.list(  # type: ignore[assignment]
                    filter=(F("spec.importer_data.project_uuid") == p.uuid),
                    max_pages=args.dep_metadata_max_pages,
                    page_size=args.page_size,
                )
            except (ValueError, TypeError, RuntimeError) as e:
                LOGGER.debug("dep metadata for project %s: %s", p.uuid, e)
                drows = []
            n_dep += len(drows)
            for d in drows or []:
                sp = _object_to_spec_dict(d)
                for tpl in row_to_supporting_tuples(
                    sp,
                    project_set,
                    include_public=bool(args.include_public),
                    produced_by=produced_by,
                    produced_name_only=produced_name,
                ):
                    all_support.append(tpl)
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
                1
                for e in edges
                if e.get("evidence_tier") == "tier_b_name_only"
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
