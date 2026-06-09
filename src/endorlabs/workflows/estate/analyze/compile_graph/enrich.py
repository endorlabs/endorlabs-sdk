"""Post-build graph enrichment from workspace corpus and project artifacts."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from endorlabs.tools.dependency_explorer import write_json
from endorlabs.workflows.estate.collect.dependency_metadata import (
    dep_data_from_record,
    load_dependency_metadata_records,
)
from endorlabs.workflows.estate.collect.projects import load_project_records
from endorlabs.workflows.estate.contracts.ir_artifacts import (
    CLUSTERING_GRAPH_IR,
    CLUSTERING_GRAPH_SCHEMA,
    COMPILE_DEPENDENCY_GRAPH_ENRICHED_IR,
    COMPILE_DEPENDENCY_GRAPH_ENRICHED_SCHEMA,
    COMPILE_DEPENDENCY_GRAPH_IR,
)
from endorlabs.workflows.estate.workspace.paths import ir_path


@dataclass
class EnrichResult:
    """Outputs from enrich_graph phase."""

    enriched: dict[str, Any]
    clustering_graph: dict[str, Any]


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


_dep_data = dep_data_from_record


def _load_cardinality_json(path: Path) -> dict[str, int]:
    """Map package_name -> version cardinality from IR JSON."""
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("packages") or data.get("rows") or []
    out: dict[str, int] = {}
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("package_name") or "").strip()
            if not name:
                continue
            raw = row.get("version_cardinality")
            try:
                val = int(raw) if raw is not None else 0
            except (TypeError, ValueError):
                val = 0
            out[name] = max(out.get(name, 0), val)
    return out


def _load_cardinality_csv(path: Path) -> dict[str, int]:
    """Map package_name -> max version cardinality from analytics export."""
    if not path.is_file():
        return {}
    out: dict[str, int] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = (row.get("package_name") or row.get("Package") or "").strip()
            if not name:
                continue
            raw = (
                row.get("version_cardinality")
                or row.get("usage_count")
                or row.get("count")
            )
            try:
                val = int(raw) if raw is not None else 1
            except (TypeError, ValueError):
                val = 1
            out[name] = max(out.get(name, 0), val)
    return out


def _load_risk_cardinality_json(path: Path) -> dict[str, dict[str, Any]]:
    """Map package_name -> risk summary from risk_cardinality JSON document."""
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    packages = data.get("packages") or []
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(packages, list):
        return out
    for pkg in packages:
        if not isinstance(pkg, dict):
            continue
        name = str(pkg.get("package_name") or "")
        if not name:
            continue
        out[name] = {
            "risk_score": float(pkg.get("risk_score") or 0),
            "findings_critical": int(pkg.get("findings_critical") or 0),
            "findings_high": int(pkg.get("findings_high") or 0),
            "findings_total": int(pkg.get("findings_total") or 0),
            "version_cardinality": int(pkg.get("version_cardinality") or 0),
        }
    return out


def _project_uuid_set(node: dict[str, Any]) -> set[str]:
    uuids = node.get("project_uuids") or []
    if node.get("project_uuid"):
        uuids = [*uuids, node["project_uuid"]]
    return {str(u) for u in uuids if u}


def enrich_graph(
    import_graph: dict[str, Any],
    *,
    discover_rows: list[dict[str, Any]],
    corpus_records: list[dict[str, Any]],
    cardinality_by_package: dict[str, int] | None = None,
    risk_by_package: dict[str, dict[str, Any]] | None = None,
) -> EnrichResult:
    """Join corpus and discover metadata onto compile-import graph nodes and edges."""
    cardinality_by_package = cardinality_by_package or {}
    risk_by_package = risk_by_package or {}
    discover_by_uuid = {str(r["uuid"]): r for r in discover_rows if r.get("uuid")}

    corpus_by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in corpus_records:
        corpus_by_project[str(rec.get("project_uuid", ""))].append(rec)

    nodes = [dict(n) for n in import_graph.get("nodes") or []]
    edges = [dict(e) for e in import_graph.get("edges") or []]
    node_by_id = {int(n["node_id"]): n for n in nodes if "node_id" in n}
    edge_pairs = {
        (int(e["importer_vertex_id"]), int(e["producer_vertex_id"])) for e in edges
    }

    for node in nodes:
        uuids = _project_uuid_set(node)
        tags: set[str] = set()
        namespaces: set[str] = set()
        direct_count = 0
        oss_count = 0
        for uid in uuids:
            disc = discover_by_uuid.get(uid, {})
            for tag in disc.get("tags") or []:
                tags.add(str(tag))
            for ns in disc.get("namespaces") or []:
                namespaces.add(str(ns))
            if disc.get("namespace"):
                namespaces.add(str(disc["namespace"]))
            for rec in corpus_by_project.get(uid, []):
                dep = _dep_data(rec)
                if dep.get("direct"):
                    direct_count += 1
                if str(dep.get("namespace") or "") == "oss":
                    oss_count += 1
        node["tags"] = sorted(tags)
        node["namespaces"] = sorted(namespaces) or node.get("namespaces", [])
        node["corpus_dependency_count"] = sum(
            len(corpus_by_project.get(uid, [])) for uid in uuids
        )
        node["corpus_direct_count"] = direct_count
        node["corpus_oss_dependency_count"] = oss_count
        node["published_package_count"] = len(node.get("published_packages") or [])
        ecosystems = {
            str(p.get("package_name", "")).split("://", 1)[0]
            for p in (node.get("published_packages") or [])
            if p.get("package_name")
        }
        node["primary_ecosystem"] = sorted(ecosystems)[0] if ecosystems else None
        pkg_names = {
            str(p.get("package_name"))
            for p in (node.get("published_packages") or [])
            if p.get("package_name")
        }
        if pkg_names and cardinality_by_package:
            node["version_cardinality_max"] = max(
                cardinality_by_package.get(name, 0) for name in pkg_names
            )
        if pkg_names and risk_by_package:
            risk_scores = [
                float(risk_by_package.get(name, {}).get("risk_score") or 0)
                for name in pkg_names
                if name in risk_by_package
            ]
            if risk_scores:
                node["risk_score_max"] = max(risk_scores)
                node["findings_critical_max"] = max(
                    int(risk_by_package.get(name, {}).get("findings_critical") or 0)
                    for name in pkg_names
                    if name in risk_by_package
                )
                node["findings_high_max"] = max(
                    int(risk_by_package.get(name, {}).get("findings_high") or 0)
                    for name in pkg_names
                    if name in risk_by_package
                )

    for edge in edges:
        importer_id = int(edge["importer_vertex_id"])
        producer_id = int(edge["producer_vertex_id"])
        linking_pkg = str(edge.get("linking_package_name") or "")
        importer_node = node_by_id.get(importer_id, {})
        importer_uuids = _project_uuid_set(importer_node)
        versions: set[str] = set()
        scopes: set[str] = set()
        licenses: set[str] = set()
        row_count = 0
        oss_backed = False
        for uid in importer_uuids:
            for rec in corpus_by_project.get(uid, []):
                dep = _dep_data(rec)
                if str(dep.get("package_name") or "") != linking_pkg:
                    continue
                row_count += 1
                ver = dep.get("resolved_version") or dep.get("unresolved_version")
                if ver:
                    versions.add(str(ver))
                if dep.get("scope"):
                    scopes.add(str(dep["scope"]))
                if str(dep.get("namespace") or "") == "oss":
                    oss_backed = True
                for field in ("declared_licenses", "discovered_licenses"):
                    lic_list = dep.get(field)
                    if isinstance(lic_list, list):
                        for lic in lic_list:
                            if isinstance(lic, dict) and lic.get("spdx_id"):
                                licenses.add(str(lic["spdx_id"]))
        edge["resolved_versions"] = sorted(versions)
        edge["version_cardinality_on_edge"] = len(versions)
        edge["scopes"] = sorted(scopes)
        edge["license_spdx_ids"] = sorted(licenses)
        edge["import_evidence_count"] = row_count
        edge["oss_backed"] = oss_backed
        edge["mutual_edge"] = (producer_id, importer_id) in edge_pairs

    enriched = {
        **import_graph,
        "schema": COMPILE_DEPENDENCY_GRAPH_ENRICHED_SCHEMA,
        "enriched_at": _utc_now(),
        "nodes": nodes,
        "edges": edges,
    }

    cluster_vertices = [
        {
            "id": int(n["node_id"]),
            "name": n.get("name"),
            "weight_attrs": {
                "corpus_dependency_count": n.get("corpus_dependency_count", 0),
                "in_degree": n.get("in_degree", 0),
            },
        }
        for n in nodes
    ]
    cluster_edges = [
        {
            "importer": int(e["importer_vertex_id"]),
            "producer": int(e["producer_vertex_id"]),
            "import_evidence_count": e.get("import_evidence_count") or 1,
            "linking_package_name": e.get("linking_package_name"),
        }
        for e in edges
    ]
    clustering_graph = {
        "schema": CLUSTERING_GRAPH_SCHEMA,
        "namespace": import_graph.get("namespace"),
        "generated_at": _utc_now(),
        "node_count": len(cluster_vertices),
        "edge_count": len(cluster_edges),
        "nodes": cluster_vertices,
        "edges": cluster_edges,
    }
    return EnrichResult(enriched=enriched, clustering_graph=clustering_graph)


def run_enrich_graph_phase(
    workspace_root: Path,
    *,
    cardinality_csv: Path | None = None,
    cardinality_json: Path | None = None,
    risk_cardinality_json: Path | None = None,
    use_intermediate_representation: bool = True,
) -> EnrichResult:
    def _artifact_path(name: str) -> Path:
        if use_intermediate_representation:
            return ir_path(workspace_root, name)
        return workspace_root / name

    graph_path = _artifact_path(COMPILE_DEPENDENCY_GRAPH_IR)
    import_graph = json.loads(graph_path.read_text(encoding="utf-8"))
    projects = load_project_records(workspace_root)
    discover_rows: list[dict[str, Any]] = []
    for project in projects:
        meta = project.get("meta") or {}
        tenant = project.get("tenant_meta") or {}
        discover_rows.append(
            {
                "uuid": project.get("uuid"),
                "name": meta.get("name"),
                "tags": meta.get("tags") or [],
                "namespace": tenant.get("namespace"),
            }
        )
    dm_records = load_dependency_metadata_records(workspace_root)
    cardinality: dict[str, int] = {}
    if cardinality_json is not None:
        cardinality = _load_cardinality_json(cardinality_json)
    elif cardinality_csv is not None:
        cardinality = _load_cardinality_csv(cardinality_csv)
    else:
        default_json = ir_path(workspace_root, "version_cardinality.json")
        if default_json.is_file():
            cardinality = _load_cardinality_json(default_json)
    risk_by_package = (
        _load_risk_cardinality_json(risk_cardinality_json)
        if risk_cardinality_json
        else {}
    )
    if not risk_by_package:
        default_risk = ir_path(workspace_root, "risk_cardinality.json")
        if default_risk.is_file():
            risk_by_package = _load_risk_cardinality_json(default_risk)
    result = enrich_graph(
        import_graph,
        discover_rows=discover_rows,
        corpus_records=dm_records,
        cardinality_by_package=cardinality or None,
        risk_by_package=risk_by_package or None,
    )
    write_json(
        str(_artifact_path(COMPILE_DEPENDENCY_GRAPH_ENRICHED_IR)),
        result.enriched,
        base_dir=workspace_root,
    )
    write_json(
        str(_artifact_path(CLUSTERING_GRAPH_IR)),
        result.clustering_graph,
        base_dir=workspace_root,
    )
    return result
