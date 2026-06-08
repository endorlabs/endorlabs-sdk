"""Post-build graph enrichment from session corpus and discover artifacts."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from endorlabs.tools.dependency_explorer import write_json

COMPILE_DEPENDENCY_GRAPH_V2 = "endor.compile_dependency_graph.v2"
LEIDEN_INPUT_SCHEMA = "endor.leiden_input.v1"


@dataclass
class EnrichResult:
    """Outputs from enrich_graph phase."""

    enriched: dict[str, Any]
    leiden_input: dict[str, Any]


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def load_corpus_records(session_dir: Path) -> list[dict[str, Any]]:
    path = session_dir / "dependency_corpus.jsonl"
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def dep_data_from_record(record: dict[str, Any]) -> dict[str, Any]:
    row = record.get("row") or {}
    raw_spec = row.get("spec")
    spec: dict[str, Any] = raw_spec if isinstance(raw_spec, dict) else {}
    raw_dep = spec.get("dependency_data")
    return raw_dep if isinstance(raw_dep, dict) else {}


_dep_data = dep_data_from_record


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


def _project_uuid_set(node: dict[str, Any]) -> set[str]:
    uuids = node.get("project_uuids") or []
    if node.get("project_uuid"):
        uuids = [*uuids, node["project_uuid"]]
    return {str(u) for u in uuids if u}


def enrich_graph(
    flat_graph: dict[str, Any],
    *,
    discover_rows: list[dict[str, Any]],
    corpus_records: list[dict[str, Any]],
    cardinality_by_package: dict[str, int] | None = None,
) -> EnrichResult:
    """Join corpus and discover metadata onto compile graph nodes and edges."""
    cardinality_by_package = cardinality_by_package or {}
    discover_by_uuid = {str(r["uuid"]): r for r in discover_rows if r.get("uuid")}

    corpus_by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in corpus_records:
        corpus_by_project[str(rec.get("project_uuid", ""))].append(rec)

    nodes = [dict(n) for n in flat_graph.get("nodes") or []]
    edges = [dict(e) for e in flat_graph.get("edges") or []]
    node_by_id = {int(n["node_id"]): n for n in nodes if "node_id" in n}
    edge_pairs = {(int(e["source_id"]), int(e["target_id"])) for e in edges}

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

    for edge in edges:
        sid = int(edge["source_id"])
        tid = int(edge["target_id"])
        anchor = str(edge.get("anchor_package_name") or "")
        src = node_by_id.get(sid, {})
        consumer_uuids = _project_uuid_set(src)
        versions: set[str] = set()
        scopes: set[str] = set()
        licenses: set[str] = set()
        row_count = 0
        oss_backed = False
        for uid in consumer_uuids:
            for rec in corpus_by_project.get(uid, []):
                dep = _dep_data(rec)
                if str(dep.get("package_name") or "") != anchor:
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
        edge["consumer_row_count"] = row_count
        edge["oss_backed"] = oss_backed
        edge["mutual_edge"] = (tid, sid) in edge_pairs

    enriched = {
        **flat_graph,
        "schema": COMPILE_DEPENDENCY_GRAPH_V2,
        "enriched_at": _utc_now(),
        "nodes": nodes,
        "edges": edges,
    }

    leiden_nodes = [
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
    leiden_edges = [
        {
            "source": int(e["source_id"]),
            "target": int(e["target_id"]),
            "weight": e.get("consumer_row_count") or 1,
            "anchor_package_name": e.get("anchor_package_name"),
        }
        for e in edges
    ]
    leiden_input = {
        "schema": LEIDEN_INPUT_SCHEMA,
        "namespace": flat_graph.get("namespace"),
        "generated_at": _utc_now(),
        "node_count": len(leiden_nodes),
        "edge_count": len(leiden_edges),
        "nodes": leiden_nodes,
        "edges": leiden_edges,
    }
    return EnrichResult(enriched=enriched, leiden_input=leiden_input)


def run_enrich_graph_phase(
    session_dir: Path,
    *,
    cardinality_csv: Path | None = None,
) -> EnrichResult:
    graph_path = session_dir / "compile_dependency_graph.json"
    flat = json.loads(graph_path.read_text(encoding="utf-8"))
    discover_path = session_dir / "phase_discover_projects.json"
    discover_rows: list[dict[str, Any]] = []
    if discover_path.is_file():
        data = json.loads(discover_path.read_text(encoding="utf-8"))
        discover_rows = data.get("projects") or []
    corpus = load_corpus_records(session_dir)
    cardinality = _load_cardinality_csv(cardinality_csv) if cardinality_csv else {}
    result = enrich_graph(
        flat,
        discover_rows=discover_rows,
        corpus_records=corpus,
        cardinality_by_package=cardinality or None,
    )
    write_json(
        str(session_dir / "compile_dependency_graph_enriched.json"),
        result.enriched,
        base_dir=session_dir,
    )
    write_json(
        str(session_dir / "leiden_input.json"),
        result.leiden_input,
        base_dir=session_dir,
    )
    return result
