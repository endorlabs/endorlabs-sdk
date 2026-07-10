"""Live API project relationship map (shared by map CLI and estate analyze)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from endorlabs import F
from endorlabs.tools.list_bounds import (
    format_progress,
    is_list_truncated,
    resolve_max_pages,
)
from endorlabs.tools.list_sharding import (
    ProjectShard,
    parallel_map_shards,
    project_model_to_shard,
)
from endorlabs.utils.artifact_io import write_json
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.estate.analyze.project_map.core import (
    SupportingPackage,
    add_producer_indices,
    aggregate_project_edges,
    indirect_paths_bfs,
    row_to_supporting_tuples,
)

LOGGER = get_resource_logger(__name__)


def _object_to_spec_dict(d: Any) -> dict[str, Any]:
    if hasattr(d, "model_dump"):
        raw = d.model_dump(mode="json", warnings=False)
    else:
        raw: Any = d
    if not isinstance(raw, dict):
        return {}
    spec = raw.get("spec")
    if isinstance(spec, dict):
        return spec
    return raw


@dataclass(frozen=True, slots=True)
class RelationshipMapResult:
    """Paths and summary stats from a namespace relationship map run."""

    graph_path: Path
    paths_path: Path
    stats_path: Path
    stats: dict[str, Any]


def run_project_relationship_map(
    client: Any,
    *,
    namespace: str,
    output_dir: Path,
    include_public: bool = False,
    max_depth: int = 3,
    max_pages: int = 0,
    page_size: int = 500,
    dep_metadata_max_pages: int = 0,
    max_workers: int = 16,
    focus_producer_project_uuid: str | None = None,
) -> RelationshipMapResult:
    """Build project-to-project relationship JSON under ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    focus_uuid = (focus_producer_project_uuid or "").strip() or None
    list_max_pages = resolve_max_pages(max_pages)
    projects = client.Project.list(
        namespace=namespace,
        traverse=True,
        max_pages=list_max_pages,
        page_size=page_size,
    )
    if is_list_truncated(len(projects), max_pages=list_max_pages, page_size=page_size):
        LOGGER.warning(
            "Project list may be truncated at %d rows; use --max-pages 0 for full estate",
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
                else namespace
            ),
        }
        for p in projects
    ]
    if focus_uuid and focus_uuid not in project_set:
        LOGGER.warning(
            "focus producer project %s not in namespace project list; edges may be empty",
            focus_uuid,
        )

    pvs = client.PackageVersion.list(
        namespace=namespace,
        traverse=True,
        max_pages=list_max_pages,
        page_size=page_size,
    )
    if is_list_truncated(len(pvs), max_pages=list_max_pages, page_size=page_size):
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
        if focus_uuid and str(puid) != focus_uuid:
            continue
        n_pv += 1
        mname = pv.meta.name if pv.meta and pv.meta.name else ""
        add_producer_indices(mname, str(puid), produced_by, produced_name)
    all_support: list[tuple[str, str, SupportingPackage]] = []
    dm_max_pages = resolve_max_pages(dep_metadata_max_pages)
    dep_shards = [project_model_to_shard(p, namespace) for p in projects if p.uuid]

    def _fetch_dep_metadata(shard: ProjectShard) -> tuple[list[Any], int]:
        drows: list[Any] = []
        try:
            drows = client.DependencyMetadata.list(
                filter=(F("spec.importer_data.project_uuid") == shard.project_uuid),
                namespace=shard.namespace,
                max_pages=dm_max_pages,
                page_size=page_size,
            )
            if is_list_truncated(
                len(drows),
                max_pages=dm_max_pages,
                page_size=page_size,
            ):
                LOGGER.warning(
                    "DependencyMetadata truncated for project %s (%d rows)",
                    shard.project_uuid,
                    len(drows),
                )
        except (ValueError, TypeError, RuntimeError) as exc:
            LOGGER.debug("dep metadata for project %s: %s", shard.project_uuid, exc)
            drows = []
        support: list[tuple[str, str, SupportingPackage]] = []
        for row in drows or []:
            spec = _object_to_spec_dict(row)
            support.extend(
                row_to_supporting_tuples(
                    spec,
                    project_set,
                    include_public=include_public,
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
        max_workers=max_workers,
        progress_label="DependencyMetadata projects",
        progress_every=50,
        on_progress=_on_dep_progress,
    ):
        all_support.extend(support)
        dep_rows_total += row_count
    edges = aggregate_project_edges(all_support)
    paths = indirect_paths_bfs(
        [p["uuid"] for p in projects_json],
        edges,
        max_depth,
    )
    if focus_uuid:
        edges = [edge for edge in edges if edge.get("to_project_uuid") == focus_uuid]
        paths = [
            path for path in paths if path.get("target_project_uuid") == focus_uuid
        ]
    tier_counts: dict[str, int] = {
        "tier_a_exact": sum(
            1 for edge in edges if edge.get("evidence_tier") == "tier_a_exact"
        ),
        "tier_b_name_only": sum(
            1 for edge in edges if edge.get("evidence_tier") == "tier_b_name_only"
        ),
    }
    ts = datetime.now(UTC).isoformat() + "Z"
    graph_payload = {
        "namespace": namespace,
        "generated_at": ts,
        "focus_producer_project_uuid": focus_uuid,
        "projects": projects_json,
        "edges": edges,
    }
    paths_payload = {
        "namespace": namespace,
        "max_depth": max_depth,
        "focus_producer_project_uuid": focus_uuid,
        "paths": paths,
    }
    stats_payload = {
        "namespace": namespace,
        "focus_producer_project_uuid": focus_uuid,
        "project_count": len(projects_json),
        "package_version_count": n_pv,
        "dependency_row_count": dep_rows_total,
        "direct_project_edge_count": len(edges),
        "indirect_path_count": len(paths),
        "tier_counts": tier_counts,
    }
    graph_path = output_dir / "project_relationship_graph.json"
    paths_path = output_dir / "project_relationship_paths.json"
    stats_path = output_dir / "project_relationship_stats.json"
    write_json(str(graph_path), graph_payload, base_dir=output_dir)
    write_json(str(paths_path), paths_payload, base_dir=output_dir)
    write_json(str(stats_path), stats_payload, base_dir=output_dir)
    return RelationshipMapResult(
        graph_path=graph_path,
        paths_path=paths_path,
        stats_path=stats_path,
        stats=stats_payload,
    )
