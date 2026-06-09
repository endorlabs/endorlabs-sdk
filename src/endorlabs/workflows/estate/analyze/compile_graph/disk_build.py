"""Build compile dependency graph from workspace data (no API collect)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from endorlabs.tools.dependency_explorer import write_json
from endorlabs.workflows.estate.analyze.compile_graph.community_detection import (
    detect_communities,
)
from endorlabs.workflows.estate.analyze.compile_graph.enrich import (
    run_enrich_graph_phase,
)
from endorlabs.workflows.estate.analyze.compile_graph.pipeline import (
    aggregate_compile_dependency_edges,
    build_graph_document,
    classify_project_registrations,
    compute_producer_rankings,
)
from endorlabs.workflows.estate.analyze.graph_metrics.analytics import (
    run_graph_analytics_phase,
)
from endorlabs.workflows.estate.analyze.project_map.core import (
    add_producer_indices,
    row_to_supporting_tuples,
)
from endorlabs.workflows.estate.collect.dependency_metadata import (
    load_dependency_metadata_records,
)
from endorlabs.workflows.estate.collect.projects import load_project_records
from endorlabs.workflows.estate.contracts import RESOURCE_PACKAGE_VERSION
from endorlabs.workflows.estate.contracts.ir_artifacts import (
    COMMUNITY_DETECTION_IR,
    COMMUNITY_PROFILES_IR,
    COMPILE_DEPENDENCY_GRAPH_ENRICHED_IR,
    COMPILE_DEPENDENCY_GRAPH_IR,
    PRODUCER_RANKINGS_IR,
)
from endorlabs.workflows.estate.workspace.paths import ir_path, resource_path


def _object_to_spec_dict(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("row") or row
    if isinstance(raw, dict):
        spec = raw.get("spec")
        if isinstance(spec, dict):
            return spec
    return {}


def _discover_rows_from_projects(
    projects: list[dict[str, Any]], namespace: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for project in projects:
        meta = project.get("meta") or {}
        tenant = project.get("tenant_meta") or {}
        rows.append(
            {
                "uuid": project.get("uuid"),
                "name": meta.get("name"),
                "tags": meta.get("tags") or [],
                "namespace": tenant.get("namespace") or namespace,
            }
        )
    return rows


def _load_published_by_project(workspace_root: Path) -> dict[str, list[dict[str, Any]]]:
    path = resource_path(workspace_root, RESOURCE_PACKAGE_VERSION)
    published: dict[str, list[dict[str, Any]]] = {}
    if not path.is_file():
        return published
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        project_uuid = str(row.get("project_uuid") or "")
        if not project_uuid:
            continue
        published.setdefault(project_uuid, []).append(row)
    return published


def _build_producer_indices(
    published_by_project: dict[str, list[dict[str, Any]]],
) -> tuple[dict[tuple[str, str], set[str]], dict[str, set[str]]]:
    produced_by: dict[tuple[str, str], set[str]] = {}
    produced_name: dict[str, set[str]] = {}
    for project_uuid, rows in published_by_project.items():
        for row in rows:
            mname = str(row.get("package_version_name") or "")
            if not mname:
                pkg = str(row.get("package_name") or "")
                ver = str(row.get("package_version") or "")
                mname = f"{pkg}@{ver}" if pkg else ""
            if mname:
                add_producer_indices(mname, project_uuid, produced_by, produced_name)
    return produced_by, produced_name


def build_compile_graph_from_workspace(
    workspace_root: Path,
    *,
    namespace: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build compile-import graph and producer rankings from pulled workspace data."""
    projects_raw = load_project_records(workspace_root)
    discover_rows = _discover_rows_from_projects(projects_raw, namespace)
    graph_projects, _ = classify_project_registrations(discover_rows)
    project_set = {str(p["uuid"]) for p in graph_projects if p.get("uuid")}

    published_by_project = _load_published_by_project(workspace_root)
    produced_by, produced_name = _build_producer_indices(published_by_project)

    dm_records = load_dependency_metadata_records(workspace_root)
    all_support: list[tuple[str, str, Any]] = []
    for record in dm_records:
        project_uuid = str(record.get("project_uuid") or "")
        if project_uuid not in project_set:
            continue
        spec = _object_to_spec_dict(record)
        all_support.extend(
            row_to_supporting_tuples(
                spec,
                project_set,
                include_public=True,
                produced_by=produced_by,
                produced_name_only=produced_name,
                direct_only=True,
            )
        )

    aggregated = aggregate_compile_dependency_edges(all_support)
    import_graph = build_graph_document(
        namespace=namespace,
        projects=graph_projects,
        aggregated_edges=aggregated,
        published_by_project=published_by_project,
    )
    rankings = compute_producer_rankings(import_graph)
    return import_graph, rankings


def write_compile_graph_ir(
    workspace_root: Path,
    *,
    namespace: str,
) -> dict[str, Any]:
    import_graph, rankings = build_compile_graph_from_workspace(
        workspace_root, namespace=namespace
    )
    write_json(
        str(ir_path(workspace_root, COMPILE_DEPENDENCY_GRAPH_IR)),
        import_graph,
        base_dir=workspace_root,
    )
    write_json(
        str(ir_path(workspace_root, PRODUCER_RANKINGS_IR)),
        rankings,
        base_dir=workspace_root,
    )
    return import_graph


def run_graph_pipeline_from_workspace(
    workspace_root: Path,
    *,
    namespace: str,
    skip_metrics: bool = False,
) -> None:
    """Full disk graph pipeline: build, enrich, metrics, community detection."""
    write_compile_graph_ir(workspace_root, namespace=namespace)

    version_cardinality = ir_path(workspace_root, "version_cardinality.json")
    risk_cardinality = ir_path(workspace_root, "risk_cardinality.json")
    run_enrich_graph_phase(
        workspace_root,
        cardinality_json=version_cardinality if version_cardinality.is_file() else None,
        risk_cardinality_json=risk_cardinality if risk_cardinality.is_file() else None,
    )

    if not skip_metrics:
        run_graph_analytics_phase(workspace_root)

    enriched_path = ir_path(workspace_root, COMPILE_DEPENDENCY_GRAPH_ENRICHED_IR)
    if enriched_path.is_file():
        enriched = json.loads(enriched_path.read_text(encoding="utf-8"))
        detection_payload, _, profiles = detect_communities(enriched)
        write_json(
            str(ir_path(workspace_root, COMMUNITY_DETECTION_IR)),
            detection_payload,
            base_dir=workspace_root,
        )
        write_json(
            str(ir_path(workspace_root, COMMUNITY_PROFILES_IR)),
            profiles,
            base_dir=workspace_root,
        )
