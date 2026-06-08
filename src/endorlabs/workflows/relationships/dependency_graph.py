#!/usr/bin/env python3
"""Estate compile-dependency graph (main context, phased artifacts).

The stitched graph is **directed** (consumer → publisher on direct compile imports).
It is **not** guaranteed acyclic: mutual internal dependencies can form cycles.
Multi-hop reachability is a post-build query on ``compile_dependency_graph.json``;
this pipeline does not precompute indirect paths.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import endorlabs
from endorlabs.core.exceptions import EndorAPIError
from endorlabs.tools.dependency_explorer import parse_dep_name, write_json
from endorlabs.workflows.list_bounds import (
    count_list_delta_check,
    format_progress,
    is_list_truncated,
    list_resource_count,
    resolve_max_pages,
    truncation_message,
)
from endorlabs.workflows.relationships.context_filters import main_context_filter
from endorlabs.workflows.relationships.core import (
    add_producer_indices,
    aggregate_package_anchored_edges,
    row_to_supporting_tuples,
)
from endorlabs.workflows.relationships.graph_analytics import run_graph_analytics_phase
from endorlabs.workflows.relationships.graph_enrich import run_enrich_graph_phase
from endorlabs.workflows.relationships.masks import (
    DEP_METADATA_LIST_MASK,
    PROJECT_LIST_MASK,
    PV_PUBLISHER_LIST_MASK,
)

LOGGER = logging.getLogger(__name__)

PhaseName = Literal[
    "discover_projects",
    "filter_git_repositories",
    "build_publisher_index",
    "collect_dependencies",
    "build_graph",
    "enrich_graph",
    "graph_analytics",
    "partition_graph",
]

RegistrationType = Literal["git_repository", "binary_component"]
REGISTRATION_GIT: RegistrationType = "git_repository"
REGISTRATION_BINARY: RegistrationType = "binary_component"

COMPILE_DEPENDENCY_GRAPH_SCHEMA = "endor.compile_dependency_graph.v1"
PUBLISHER_RANKINGS_SCHEMA = "endor.publisher_rankings.v1"
GIT_URL_NAME_RE = re.compile(r"^(https?://|git@)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class _ProjectRef:
    uuid: str
    namespace: str


@dataclass
class PhaseCheck:
    """One validation check for a pipeline phase."""

    name: str
    ok: bool
    detail: str = ""


@dataclass
class PhaseValidation:
    """Validation report written beside each phase artifact."""

    phase: PhaseName
    ok: bool
    checks: list[PhaseCheck] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "ok": self.ok,
            "generated_at": self.generated_at,
            "checks": [
                {"name": c.name, "ok": c.ok, "detail": c.detail} for c in self.checks
            ],
        }


def namespace_slug(namespace: str) -> str:
    cleaned = namespace.strip().rstrip(".")
    if not cleaned:
        return "unknown"
    return cleaned.replace(".", "_")


def session_dir_for(context_dir: str | Path, namespace: str) -> Path:
    return Path(context_dir) / "session" / namespace_slug(namespace)


def is_git_url_project_name(name: str) -> bool:
    return bool(GIT_URL_NAME_RE.match(name.strip()))


def project_union_key(name: str, project_uuid: str) -> str:
    label = name.strip()
    if is_git_url_project_name(label):
        key = label.lower().rstrip("/").removesuffix(".git")
        return f"git:{key}"
    return f"uuid:{project_uuid}"


def registration_type_for_name(name: str) -> RegistrationType:
    """Classify a project registration as Git-backed or binary/component."""
    if is_git_url_project_name(name):
        return REGISTRATION_GIT
    return REGISTRATION_BINARY


def classify_project_registrations(
    project_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[RegistrationType, int]]:
    """Annotate every discover row with ``registration_type`` (all are graph nodes)."""
    classified: list[dict[str, Any]] = []
    counts: dict[RegistrationType, int] = {
        REGISTRATION_GIT: 0,
        REGISTRATION_BINARY: 0,
    }
    for row in project_rows:
        name = str(row.get("name") or "")
        reg_type = registration_type_for_name(name)
        classified.append({**row, "registration_type": reg_type})
        counts[reg_type] += 1
    return classified, counts


def filter_git_repositories(
    project_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Legacy split: Git-backed vs binary/component (neither is dropped)."""
    classified, _ = classify_project_registrations(project_rows)
    git_rows = [r for r in classified if r.get("registration_type") == REGISTRATION_GIT]
    binary_rows = [
        r for r in classified if r.get("registration_type") == REGISTRATION_BINARY
    ]
    return git_rows, binary_rows


def build_union_nodes(
    projects: list[dict[str, Any]],
    *,
    estate_namespace: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for proj in projects:
        puid = str(proj.get("uuid", ""))
        if not puid:
            continue
        name = str(proj.get("name") or puid)
        key = project_union_key(name, puid)
        groups.setdefault(key, []).append(proj)

    nodes: list[dict[str, Any]] = []
    uuid_to_node: dict[str, int] = {}
    for node_id, key in enumerate(sorted(groups.keys())):
        members = groups[key]
        uuids = sorted(str(m.get("uuid", "")) for m in members if m.get("uuid"))
        namespaces = sorted(
            {
                str(m.get("namespace") or estate_namespace)
                for m in members
                if m.get("uuid")
            }
        )
        names = [str(m.get("name") or m.get("uuid", "")) for m in members]
        canonical_name = sorted(names)[0]
        member_types = {
            str(
                m.get("registration_type")
                or registration_type_for_name(str(m.get("name") or ""))
            )
            for m in members
        }
        if REGISTRATION_GIT in member_types:
            registration_type: RegistrationType = REGISTRATION_GIT
        else:
            registration_type = REGISTRATION_BINARY
        nodes.append(
            {
                "node_id": node_id,
                "git_identity": key,
                "registration_type": registration_type,
                "name": canonical_name,
                "project_uuid": uuids[0],
                "project_uuids": uuids,
                "member_count": len(uuids),
                "namespace": (
                    namespaces[0] if len(namespaces) == 1 else estate_namespace
                ),
                "namespaces": namespaces,
            }
        )
        for uid in uuids:
            uuid_to_node[uid] = node_id
    return nodes, uuid_to_node


def _stronger_match_tier(a: str | None, b: str | None) -> str | None:
    if a == "tier_a_exact" or b == "tier_a_exact":
        return "tier_a_exact"
    if a == "tier_b_name_only" or b == "tier_b_name_only":
        return "tier_b_name_only"
    return a or b


def _merge_union_edges(
    aggregated_edges: list[dict[str, Any]],
    uuid_to_node: dict[str, int],
) -> list[dict[str, Any]]:
    merged: dict[tuple[int, int, str], dict[str, Any]] = {}
    for raw in aggregated_edges:
        fr = str(raw.get("from_project_uuid", ""))
        to = str(raw.get("to_project_uuid", ""))
        anchor = str(raw.get("anchor_package_name") or "")
        if not anchor or fr not in uuid_to_node or to not in uuid_to_node:
            continue
        sid = uuid_to_node[fr]
        tid = uuid_to_node[to]
        if sid == tid:
            continue
        key = (sid, tid, anchor)
        if key not in merged:
            merged[key] = {
                "source_id": sid,
                "target_id": tid,
                "anchor_package_name": anchor,
                "source_uuids": set(),
                "target_uuids": set(),
                "package_version": raw.get("package_version"),
                "match_tier": raw.get("match_tier"),
                "visibility": raw.get("visibility"),
            }
        row = merged[key]
        row["source_uuids"].add(fr)
        row["target_uuids"].add(to)
        row["match_tier"] = _stronger_match_tier(
            row.get("match_tier"),
            raw.get("match_tier"),
        )
        if raw.get("package_version"):
            row["package_version"] = raw.get("package_version")

    edges: list[dict[str, Any]] = []
    for row in merged.values():
        source_uuids = sorted(row["source_uuids"])
        target_uuids = sorted(row["target_uuids"])
        edges.append(
            {
                "source_id": row["source_id"],
                "target_id": row["target_id"],
                "source_uuid": source_uuids[0],
                "target_uuid": target_uuids[0],
                "source_uuids": source_uuids,
                "target_uuids": target_uuids,
                "anchor_package_name": row["anchor_package_name"],
                "package_version": row.get("package_version") or "",
                "match_tier": row.get("match_tier"),
                "import_kind": "direct",
                "visibility": row.get("visibility"),
                "dependency_scope": "compile",
                "edge_kind": "compile_dependency",
            }
        )
    return edges


def annotate_vertices(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    published_by_project: dict[str, list[dict[str, Any]]],
) -> None:
    """Attach published packages, imports, degrees, and isolated flag to each node."""
    node_by_id = {int(n["node_id"]): n for n in nodes if "node_id" in n}
    in_degree: dict[int, int] = {}
    out_degree: dict[int, int] = {}

    for node in nodes:
        uuids = node.get("project_uuids") or [node.get("project_uuid")]
        published: dict[str, dict[str, Any]] = {}
        for uid in uuids:
            for pkg in published_by_project.get(str(uid), []):
                pn = str(pkg.get("package_name") or "")
                if pn and pn not in published:
                    published[pn] = dict(pkg)
        node["published_packages"] = sorted(
            published.values(),
            key=lambda x: str(x.get("package_name") or ""),
        )
        node["direct_imports"] = []
        node["imported_by"] = []

    for edge in edges:
        sid = int(edge["source_id"])
        tid = int(edge["target_id"])
        out_degree[sid] = out_degree.get(sid, 0) + 1
        in_degree[tid] = in_degree.get(tid, 0) + 1
        src = node_by_id.get(sid, {})
        tgt = node_by_id.get(tid, {})
        entry = {
            "anchor_package_name": edge.get("anchor_package_name"),
            "package_version": edge.get("package_version"),
            "publisher_node_id": tid,
            "publisher_name": tgt.get("name"),
            "match_tier": edge.get("match_tier"),
            "visibility": edge.get("visibility"),
        }
        src.setdefault("direct_imports", []).append(entry)
        tgt.setdefault("imported_by", []).append(
            {
                "anchor_package_name": edge.get("anchor_package_name"),
                "package_version": edge.get("package_version"),
                "consumer_node_id": sid,
                "consumer_name": src.get("name"),
                "match_tier": edge.get("match_tier"),
                "visibility": edge.get("visibility"),
            }
        )

    for node in nodes:
        nid = int(node["node_id"])
        node["in_degree"] = in_degree.get(nid, 0)
        node["out_degree"] = out_degree.get(nid, 0)
        node["isolated"] = node["in_degree"] == 0 and node["out_degree"] == 0


def build_graph_document(
    *,
    namespace: str,
    projects: list[dict[str, Any]],
    aggregated_edges: list[dict[str, Any]],
    published_by_project: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    nodes, uuid_to_node = build_union_nodes(projects, estate_namespace=namespace)
    edges = _merge_union_edges(aggregated_edges, uuid_to_node)
    annotate_vertices(nodes, edges, published_by_project=published_by_project)
    isolated_count = sum(1 for n in nodes if n.get("isolated"))
    return {
        "schema": COMPILE_DEPENDENCY_GRAPH_SCHEMA,
        "namespace": namespace,
        "context": {"type": "CONTEXT_TYPE_MAIN"},
        "generated_at": _utc_now(),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "isolated_count": isolated_count,
        "project_registration_count": len(projects),
        "nodes": nodes,
        "edges": edges,
    }


def aggregate_compile_dependency_edges(
    supporting: list[tuple[str, str, Any]],
) -> list[dict[str, Any]]:
    return aggregate_package_anchored_edges(supporting)


def compute_publisher_rankings(
    flat_graph: dict[str, Any],
    *,
    top_n: int = 50,
) -> dict[str, Any]:
    nodes = flat_graph.get("nodes") or []
    edges = flat_graph.get("edges") or []
    node_by_id = {int(n["node_id"]): n for n in nodes if "node_id" in n}

    inbound_edges: dict[int, int] = {}
    consumer_nodes: dict[int, set[int]] = {}
    anchor_names: dict[int, set[str]] = {}

    for edge in edges:
        sid = int(edge["source_id"])
        tid = int(edge["target_id"])
        inbound_edges[tid] = inbound_edges.get(tid, 0) + 1
        consumer_nodes.setdefault(tid, set()).add(sid)
        anchor = edge.get("anchor_package_name")
        if anchor:
            anchor_names.setdefault(tid, set()).add(str(anchor))

    sorted_targets = sorted(inbound_edges.items(), key=lambda item: (-item[1], item[0]))
    rankings: list[dict[str, Any]] = []
    for rank, (nid, edge_count) in enumerate(sorted_targets[:top_n], start=1):
        node = node_by_id.get(nid, {})
        anchors = sorted(anchor_names.get(nid, set()))
        rankings.append(
            {
                "rank": rank,
                "node_id": nid,
                "project_uuid": node.get("project_uuid"),
                "project_uuids": node.get("project_uuids")
                or [node.get("project_uuid")],
                "member_count": node.get("member_count", 1),
                "git_identity": node.get("git_identity"),
                "registration_type": node.get("registration_type"),
                "name": node.get("name"),
                "namespace": node.get("namespace"),
                "namespaces": node.get("namespaces") or [node.get("namespace")],
                "consumer_count": len(consumer_nodes.get(nid, set())),
                "inbound_edge_count": edge_count,
                "sample_anchor_packages": anchors[:10],
                "anchor_package_count": len(anchors),
            }
        )

    return {
        "schema": PUBLISHER_RANKINGS_SCHEMA,
        "namespace": flat_graph.get("namespace"),
        "generated_at": _utc_now(),
        "total_nodes": len(nodes),
        "isolated_count": flat_graph.get("isolated_count", 0),
        "project_registration_count": flat_graph.get("project_registration_count"),
        "total_edges": len(edges),
        "publishers_with_consumers": len(inbound_edges),
        "top_n": top_n,
        "rankings": rankings,
    }


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


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _write_phase(
    session_dir: Path,
    phase: PhaseName,
    payload: dict[str, Any],
    validation: PhaseValidation,
) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        str(session_dir / f"phase_{phase}.json"),
        payload,
        base_dir=session_dir,
    )
    write_json(
        str(session_dir / f"phase_{phase}_validation.json"),
        validation.to_dict(),
        base_dir=session_dir,
    )


def _read_validation(session_dir: Path, phase: PhaseName) -> PhaseValidation | None:
    path = session_dir / f"phase_{phase}_validation.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    checks = [
        PhaseCheck(name=c["name"], ok=bool(c["ok"]), detail=c.get("detail", ""))
        for c in data.get("checks", [])
    ]
    return PhaseValidation(
        phase=phase,
        ok=bool(data.get("ok")),
        checks=checks,
        generated_at=str(data.get("generated_at", "")),
    )


def require_prior_phase(session_dir: Path, phase: PhaseName) -> PhaseValidation:
    val = _read_validation(session_dir, phase)
    if val is None:
        msg = f"Missing validation for phase {phase} under {session_dir}"
        raise FileNotFoundError(msg)
    if not val.ok:
        msg = f"Prior phase {phase} did not pass validation ({session_dir})"
        raise RuntimeError(msg)
    return val


def _project_row_from_item(item: Any, namespace: str) -> dict[str, Any] | None:
    if isinstance(item, dict):
        uuid = item.get("uuid")
        if not uuid:
            return None
        raw_meta = item.get("meta")
        meta: dict[str, Any] = raw_meta if isinstance(raw_meta, dict) else {}
        raw_tenant = item.get("tenant_meta")
        tenant: dict[str, Any] = raw_tenant if isinstance(raw_tenant, dict) else {}
        raw_spec = item.get("spec")
        spec_dict: dict[str, Any] = raw_spec if isinstance(raw_spec, dict) else {}
        raw_tags = meta.get("tags")
        raw_namespaces = spec_dict.get("namespaces")
        return {
            "uuid": str(uuid),
            "name": str(meta.get("name") or uuid),
            "namespace": str(tenant.get("namespace") or namespace),
            "tags": raw_tags if isinstance(raw_tags, list) else [],
            "registration_type": spec_dict.get("registration_type"),
            "namespaces": raw_namespaces if isinstance(raw_namespaces, list) else [],
        }
    if not getattr(item, "uuid", None):
        return None
    item_spec = getattr(item, "spec", None)
    return {
        "uuid": str(item.uuid),
        "name": (item.meta.name if item.meta and item.meta.name else item.uuid),
        "namespace": (
            item.tenant_meta.namespace
            if item.tenant_meta and item.tenant_meta.namespace
            else namespace
        ),
        "tags": (list(item.meta.tags) if item.meta and item.meta.tags else []),
        "registration_type": (
            getattr(item_spec, "registration_type", None) if item_spec else None
        ),
        "namespaces": (
            list(item_spec.namespaces)
            if item_spec and getattr(item_spec, "namespaces", None)
            else []
        ),
    }


def _project_rows_from_models(
    projects: list[Any], namespace: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in projects:
        row = _project_row_from_item(item, namespace)
        if row:
            rows.append(row)
    return rows


def _corpus_record_from_row(row: Any, *, project_uuid: str) -> dict[str, Any]:
    if isinstance(row, dict):
        payload: dict[str, Any] = row
    else:
        payload = {"spec": _object_to_spec_dict(row)}
    return {
        "project_uuid": project_uuid,
        "dm_uuid": payload.get("uuid"),
        "row": payload,
    }


def _project_refs(
    project_rows: list[dict[str, Any]], default_namespace: str
) -> list[_ProjectRef]:
    return [
        _ProjectRef(
            uuid=str(r["uuid"]),
            namespace=str(r.get("namespace") or default_namespace),
        )
        for r in project_rows
        if r.get("uuid")
    ]


def _load_discover_rows(session_dir: Path) -> list[dict[str, Any]]:
    data = json.loads(
        (session_dir / "phase_discover_projects.json").read_text(encoding="utf-8")
    )
    return data.get("projects") or []


def _load_graph_project_rows(session_dir: Path) -> list[dict[str, Any]]:
    data = json.loads(
        (session_dir / "phase_filter_git_repositories.json").read_text(encoding="utf-8")
    )
    rows = data.get("graph_projects") or data.get("included_projects") or []
    if rows and "registration_type" not in rows[0]:
        classified, _ = classify_project_registrations(rows)
        return classified
    return rows


def _pv_row_uuid(row: Any) -> str | None:
    if isinstance(row, dict):
        return row.get("uuid")
    return getattr(row, "uuid", None)


def _pv_project_uuid(row: Any) -> str | None:
    if isinstance(row, dict):
        spec = row.get("spec")
        if isinstance(spec, dict):
            return spec.get("project_uuid")
        return None
    if row.spec:
        return getattr(row.spec, "project_uuid", None)
    return None


def _pv_meta_name(row: Any) -> str:
    if isinstance(row, dict):
        meta = row.get("meta")
        if isinstance(meta, dict):
            return str(meta.get("name") or "")
        return ""
    if row.meta and row.meta.name:
        return str(row.meta.name)
    return ""


def discover_projects(
    client: endorlabs.Client,
    *,
    namespace: str,
    max_pages: int | None,
    page_size: int,
    max_workers: int = 10,
) -> tuple[list[dict[str, Any]], PhaseValidation, int | None]:
    in_scope_count = list_resource_count(
        client.Project,
        namespace,
        resource_label="Project",
        traverse=True,
        logger=LOGGER,
    )
    projects = client.Project.list(
        namespace=namespace,
        traverse=True,
        max_workers=max_workers,
        max_pages=max_pages,
        page_size=page_size,
        mask=PROJECT_LIST_MASK,
    )
    rows = _project_rows_from_models(projects, namespace)
    list_truncated = is_list_truncated(
        len(projects), max_pages=max_pages, page_size=page_size
    )
    if list_truncated:
        LOGGER.warning(
            "%s",
            truncation_message(
                resource="Project",
                scope=f"namespace={namespace}",
                row_count=len(projects),
                max_pages=max_pages,
                page_size=page_size,
            ),
        )
    git_named = sum(1 for r in rows if is_git_url_project_name(str(r.get("name", ""))))
    checks = [
        PhaseCheck("project_count_gt_zero", len(rows) > 0, f"{len(rows)} projects"),
        PhaseCheck(
            "git_url_names_majority",
            len(rows) == 0 or git_named >= max(1, len(rows) // 2),
            f"{git_named}/{len(rows)} Git-URL names",
        ),
        PhaseCheck(
            "all_projects_have_uuid",
            all(r.get("uuid") for r in rows),
            "uuid present on every row",
        ),
        PhaseCheck(
            "project_list_not_truncated",
            not list_truncated,
            (
                f"Project list capped at {len(projects)} rows"
                if list_truncated
                else "Project list complete within cap"
            ),
        ),
    ]
    count_ok, count_detail = count_list_delta_check(
        in_scope_count=in_scope_count,
        actual_row_count=len(rows),
    )
    checks.append(PhaseCheck("count_matches_list", count_ok, count_detail))
    validation = PhaseValidation(
        phase="discover_projects",
        ok=all(c.ok for c in checks),
        checks=checks,
        generated_at=_utc_now(),
    )
    return rows, validation, in_scope_count


def run_filter_git_repositories(
    project_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[RegistrationType, int], PhaseValidation]:
    graph_projects, registration_counts = classify_project_registrations(project_rows)
    checks = [
        PhaseCheck(
            "graph_projects_gt_zero",
            len(graph_projects) > 0,
            f"{len(graph_projects)} graph nodes",
        ),
        PhaseCheck(
            "registration_types_documented",
            True,
            (
                f"{registration_counts[REGISTRATION_GIT]} git_repository, "
                f"{registration_counts[REGISTRATION_BINARY]} binary_component"
            ),
        ),
    ]
    validation = PhaseValidation(
        phase="filter_git_repositories",
        ok=checks[0].ok,
        checks=checks,
        generated_at=_utc_now(),
    )
    return graph_projects, registration_counts, validation


def build_publisher_index(
    client: endorlabs.Client,
    *,
    namespace: str,
    project_set: set[str],
    max_pages: int | None,
    page_size: int,
    max_workers: int = 10,
) -> tuple[
    dict[tuple[str, str], set[str]],
    dict[str, set[str]],
    dict[str, list[dict[str, Any]]],
    int,
    PhaseValidation,
    int | None,
]:
    pv_filter = main_context_filter()
    in_scope_count = list_resource_count(
        client.PackageVersion,
        namespace,
        resource_label="PackageVersion",
        filter_expr=pv_filter,
        traverse=True,
        logger=LOGGER,
    )
    pvs = client.PackageVersion.list(
        namespace=namespace,
        traverse=True,
        max_workers=max_workers,
        filter=pv_filter,
        max_pages=max_pages,
        page_size=page_size,
        mask=PV_PUBLISHER_LIST_MASK,
    )
    produced_by: dict[tuple[str, str], set[str]] = {}
    produced_name: dict[str, set[str]] = {}
    published_by_project: dict[str, list[dict[str, Any]]] = {}
    n_pv = 0
    for pv in pvs:
        puid = _pv_project_uuid(pv)
        if not puid or str(puid) not in project_set:
            continue
        n_pv += 1
        mname = _pv_meta_name(pv)
        add_producer_indices(mname, str(puid), produced_by, produced_name)
        pkg_name, pkg_ver = parse_dep_name(mname)
        published_by_project.setdefault(str(puid), []).append(
            {
                "package_name": pkg_name,
                "package_version_name": mname,
                "package_version": pkg_ver,
                "pv_uuid": _pv_row_uuid(pv),
            }
        )
    pv_list_truncated = is_list_truncated(
        len(pvs), max_pages=max_pages, page_size=page_size
    )
    if pv_list_truncated:
        LOGGER.warning(
            "%s",
            truncation_message(
                resource="PackageVersion",
                scope=f"namespace={namespace}",
                row_count=len(pvs),
                max_pages=max_pages,
                page_size=page_size,
            ),
        )
    checks = [
        PhaseCheck(
            "publisher_rows_gt_zero",
            n_pv > 0 or len(project_set) == 0,
            f"{n_pv} package versions indexed",
        ),
        PhaseCheck(
            "publisher_name_index_nonempty",
            len(produced_name) > 0 or n_pv == 0,
            f"{len(produced_name)} distinct package names",
        ),
        PhaseCheck(
            "package_version_list_not_truncated",
            not pv_list_truncated,
            (
                f"PackageVersion list capped at {len(pvs)} rows"
                if pv_list_truncated
                else "PackageVersion list complete within cap"
            ),
        ),
    ]
    count_ok, count_detail = count_list_delta_check(
        in_scope_count=in_scope_count,
        actual_row_count=len(pvs),
    )
    checks.append(PhaseCheck("count_matches_list", count_ok, count_detail))
    LOGGER.info(
        "%s",
        format_progress(
            "PackageVersion index",
            n_pv,
            in_scope_count,
            extra=f"{len(pvs)} listed rows",
        ),
    )
    validation = PhaseValidation(
        phase="build_publisher_index",
        ok=all(c.ok for c in checks),
        checks=checks,
        generated_at=_utc_now(),
    )
    return (
        produced_by,
        produced_name,
        published_by_project,
        n_pv,
        validation,
        in_scope_count,
    )


def _fetch_project_dependencies(
    client: endorlabs.Client,
    project: _ProjectRef,
    *,
    dep_metadata_max_pages: int,
    page_size: int,
    project_set: set[str],
    produced_by: dict[tuple[str, str], set[str]],
    produced_name: dict[str, set[str]],
) -> tuple[str, list[tuple[str, str, Any]], int, bool, list[dict[str, Any]]]:
    filt = main_context_filter(f'spec.importer_data.project_uuid=="{project.uuid}"')
    dm_max_pages = resolve_max_pages(dep_metadata_max_pages)
    rows = client.DependencyMetadata.list(
        filter=filt,
        namespace=project.namespace,
        max_pages=dm_max_pages,
        page_size=page_size,
        mask=DEP_METADATA_LIST_MASK,
    )
    n_rows = len(rows or [])
    corpus_rows = [
        _corpus_record_from_row(d, project_uuid=project.uuid) for d in (rows or [])
    ]
    truncated = is_list_truncated(n_rows, max_pages=dm_max_pages, page_size=page_size)
    if truncated:
        LOGGER.warning(
            "%s",
            truncation_message(
                resource="DependencyMetadata",
                scope=f"project={project.uuid}",
                row_count=n_rows,
                max_pages=dm_max_pages,
                page_size=page_size,
            ),
        )
    support: list[tuple[str, str, Any]] = []
    for d in rows or []:
        sp = _object_to_spec_dict(d)
        support.extend(
            row_to_supporting_tuples(
                sp,
                project_set,
                include_public=True,
                produced_by=produced_by,
                produced_name_only=produced_name,
                direct_only=True,
            )
        )
    return project.uuid, support, n_rows, truncated, corpus_rows


def _append_corpus_records(
    handle: Any,
    records: list[dict[str, Any]],
) -> None:
    for record in records:
        handle.write(json.dumps(record, ensure_ascii=False))
        handle.write("\n")


def _write_corpus_manifest(
    session_dir: Path,
    *,
    namespace: str,
    record_count: int,
) -> None:
    write_json(
        str(session_dir / "dependency_corpus_manifest.json"),
        {
            "namespace": namespace,
            "generated_at": _utc_now(),
            "record_count": record_count,
            "path": "dependency_corpus.jsonl",
        },
        base_dir=session_dir,
    )


def _write_collect_fetch_errors(
    session_dir: Path,
    errors: list[str],
) -> None:
    rows: list[dict[str, str]] = []
    for entry in errors:
        uuid, _, msg = entry.partition(":")
        rows.append({"project_uuid": uuid.strip(), "error": msg.strip() or entry})
    write_json(
        str(session_dir / "collect_fetch_errors.json"),
        {
            "generated_at": _utc_now(),
            "error_count": len(rows),
            "errors": rows,
        },
        base_dir=session_dir,
    )


def _load_collect_fetch_error_uuids(session_dir: Path) -> set[str]:
    path = session_dir / "collect_fetch_errors.json"
    if not path.is_file():
        msg = f"Missing {path}; run collect_dependencies first"
        raise FileNotFoundError(msg)
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("errors") or []
    return {
        str(row["project_uuid"])
        for row in rows
        if isinstance(row, dict) and row.get("project_uuid")
    }


def _configure_session_logging(session_dir: Path) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    log_path = session_dir / "pipeline_run.log"
    root = logging.getLogger()
    for handler in root.handlers:
        if getattr(handler, "baseFilename", None) == str(log_path.resolve()):
            return
    fh = logging.FileHandler(log_path, encoding="utf-8", mode="a")
    fh.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    fh.setLevel(logging.INFO)
    root.addHandler(fh)


def collect_dependencies(
    client: endorlabs.Client,
    *,
    projects: list[_ProjectRef],
    project_set: set[str],
    produced_by: dict[tuple[str, str], set[str]],
    produced_name: dict[str, set[str]],
    dep_metadata_max_pages: int,
    page_size: int,
    max_workers: int,
    session_dir: Path | None = None,
    corpus_append: bool = False,
    count_in_scope: int | None = None,
) -> tuple[
    list[tuple[str, str, Any]],
    int,
    PhaseValidation,
    list[str],
    int | None,
    list[dict[str, Any]],
    list[str],
]:
    all_support: list[tuple[str, str, Any]] = []
    total_rows = 0
    errors: list[str] = []
    truncated_projects: list[str] = []

    def _count_dm(project: _ProjectRef) -> int:
        filt = main_context_filter(f'spec.importer_data.project_uuid=="{project.uuid}"')
        return (
            list_resource_count(
                client.DependencyMetadata,
                project.namespace,
                resource_label="DependencyMetadata",
                filter_expr=filt,
                logger=LOGGER,
            )
            or 0
        )

    workers = max(1, min(max_workers, len(projects) or 1))
    expected_dm_rows: int | None = 0
    if projects:
        with ThreadPoolExecutor(max_workers=workers) as count_pool:
            count_futures = [count_pool.submit(_count_dm, p) for p in projects]
            expected_dm_rows = sum(f.result() for f in count_futures)
        LOGGER.info(
            "DependencyMetadata preflight: expected_dm_rows=%s across %d projects",
            expected_dm_rows,
            len(projects),
        )

    def _work(
        project: _ProjectRef,
    ) -> tuple[str, list[tuple[str, str, Any]], int, bool, list[dict[str, Any]]]:
        return _fetch_project_dependencies(
            client,
            project,
            dep_metadata_max_pages=dep_metadata_max_pages,
            page_size=page_size,
            project_set=project_set,
            produced_by=produced_by,
            produced_name=produced_name,
        )

    all_corpus: list[dict[str, Any]] = []
    corpus_handle: Any | None = None
    prior_corpus_rows = 0
    if session_dir is not None:
        session_dir.mkdir(parents=True, exist_ok=True)
        corpus_path = session_dir / "dependency_corpus.jsonl"
        if corpus_append and corpus_path.is_file():
            with corpus_path.open(encoding="utf-8") as handle:
                prior_corpus_rows = sum(1 for _ in handle)
        corpus_handle = corpus_path.open(
            "a" if corpus_append and corpus_path.is_file() else "w",
            encoding="utf-8",
        )

    completed = 0
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_work, pref): pref for pref in projects}
            for fut in as_completed(futures):
                pref = futures[fut]
                try:
                    _, support, n_rows, truncated, corpus_rows = fut.result()
                    all_support.extend(support)
                    total_rows += n_rows
                    if corpus_handle is not None:
                        _append_corpus_records(corpus_handle, corpus_rows)
                    else:
                        all_corpus.extend(corpus_rows)
                    if truncated:
                        truncated_projects.append(pref.uuid)
                except (ValueError, TypeError, RuntimeError, EndorAPIError) as exc:
                    errors.append(f"{pref.uuid}: {exc}")
                    LOGGER.warning(
                        "dependency fetch failed for project %s: %s",
                        pref.uuid,
                        exc,
                    )
                completed += 1
                if completed % 50 == 0 or completed == len(projects):
                    LOGGER.info(
                        "%s, %s",
                        format_progress(
                            "DependencyMetadata projects",
                            completed,
                            len(projects),
                        ),
                        format_progress(
                            "DependencyMetadata rows",
                            prior_corpus_rows + total_rows,
                            expected_dm_rows if projects else None,
                            extra=f"{len(all_support)} tuples",
                        ),
                    )
    finally:
        if corpus_handle is not None:
            corpus_handle.close()

    counted_rows = prior_corpus_rows + total_rows
    checks = [
        PhaseCheck(
            "dependency_rows_gt_zero",
            counted_rows > 0 or len(projects) == 0,
            f"{counted_rows} DependencyMetadata rows",
        ),
        PhaseCheck(
            "fetch_errors_below_half",
            len(errors) < max(1, len(projects) // 2),
            f"{len(errors)} project fetch errors",
        ),
        PhaseCheck(
            "no_dep_metadata_truncation",
            len(truncated_projects) == 0,
            (
                f"{len(truncated_projects)} projects hit dep-metadata page cap"
                if truncated_projects
                else "all project DM lists complete within cap"
            ),
        ),
    ]
    in_scope_for_check = (
        count_in_scope if count_in_scope is not None else expected_dm_rows
    )
    count_ok, count_detail = count_list_delta_check(
        in_scope_count=in_scope_for_check if projects else None,
        actual_row_count=counted_rows,
    )
    checks.append(PhaseCheck("count_matches_list", count_ok, count_detail))
    validation = PhaseValidation(
        phase="collect_dependencies",
        ok=all(c.ok for c in checks),
        checks=checks,
        generated_at=_utc_now(),
    )
    return (
        all_support,
        total_rows,
        validation,
        truncated_projects,
        expected_dm_rows if projects else None,
        all_corpus,
        errors,
    )


def _load_collected_direct_edges(session_dir: Path) -> list[dict[str, Any]] | None:
    path = session_dir / "collected_direct_edges.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    edges = data.get("edges")
    return edges if isinstance(edges, list) else None


def _save_collected_direct_edges(
    session_dir: Path,
    *,
    namespace: str,
    edges: list[dict[str, Any]],
    supporting_tuple_count: int,
) -> None:
    write_json(
        str(session_dir / "collected_direct_edges.json"),
        {
            "namespace": namespace,
            "generated_at": _utc_now(),
            "supporting_tuple_count": supporting_tuple_count,
            "direct_edge_count": len(edges),
            "edges": edges,
        },
        base_dir=session_dir,
    )


@dataclass(frozen=True, slots=True)
class PartitionOptions:
    """Leiden partition tuning knobs."""

    resolution: float = 1.0
    iterations: int = 10
    weight_field: Literal["none", "consumer_row_count", "inbound_rank"] = "none"
    component_min_size: int = 1
    seed: int = 42


def _partition_weights(
    graph: dict[str, Any],
    *,
    weight_field: str,
) -> list[float] | None:
    if weight_field == "none":
        return None
    nodes = graph.get("nodes") or []
    if weight_field == "inbound_rank":
        in_deg = {int(n["node_id"]): int(n.get("in_degree") or 0) for n in nodes}
        return [float(max(1, in_deg.get(i, 0))) for i in range(len(nodes))]
    return None


def _edge_weights_for_partition(
    graph: dict[str, Any],
    *,
    weight_field: str,
) -> list[float] | None:
    if weight_field != "consumer_row_count":
        return None
    edges = graph.get("edges") or []
    return [float(max(1, e.get("consumer_row_count") or 1)) for e in edges]


def _build_community_summary(
    graph: dict[str, Any],
    communities: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    node_by_id = {int(n["node_id"]): n for n in nodes if "node_id" in n}
    rows: list[dict[str, Any]] = []
    for comm in communities:
        node_ids = [int(i) for i in comm.get("node_ids") or []]
        comm_nodes = [node_by_id[i] for i in node_ids if i in node_by_id]
        namespaces: dict[str, int] = {}
        tags: dict[str, int] = {}
        anchors: dict[str, int] = {}
        in_deg: dict[int, int] = {}
        for edge in edges:
            tid = int(edge.get("target_id", -1))
            if tid in node_ids:
                in_deg[tid] = in_deg.get(tid, 0) + 1
                anchor = str(edge.get("anchor_package_name") or "")
                if anchor:
                    anchors[anchor] = anchors.get(anchor, 0) + 1
        for node in comm_nodes:
            for ns in node.get("namespaces") or [node.get("namespace")]:
                if ns:
                    namespaces[str(ns)] = namespaces.get(str(ns), 0) + 1
            for tag in node.get("tags") or []:
                tags[str(tag)] = tags.get(str(tag), 0) + 1
        hub_ids = sorted(in_deg.items(), key=lambda x: (-x[1], x[0]))[:10]
        rows.append(
            {
                "community_id": comm.get("community_id"),
                "node_count": len(node_ids),
                "edge_count": sum(
                    1
                    for e in edges
                    if int(e.get("source_id", -1)) in node_ids
                    and int(e.get("target_id", -1)) in node_ids
                ),
                "dominant_namespaces": sorted(
                    namespaces.items(), key=lambda x: (-x[1], x[0])
                )[:5],
                "top_tags": sorted(tags.items(), key=lambda x: (-x[1], x[0]))[:5],
                "top_anchor_packages": sorted(
                    anchors.items(), key=lambda x: (-x[1], x[0])
                )[:10],
                "hub_node_ids": [i for i, _ in hub_ids],
            }
        )
    return {
        "schema": "endor.community_summary.v1",
        "namespace": graph.get("namespace"),
        "generated_at": _utc_now(),
        "communities": rows,
    }


def _load_partition_graph_input(session_dir: Path) -> dict[str, Any]:
    leiden_path = session_dir / "leiden_input.json"
    if leiden_path.is_file():
        leiden = json.loads(leiden_path.read_text(encoding="utf-8"))
        nodes = []
        for item in leiden.get("nodes") or []:
            nodes.append(
                {
                    "node_id": item.get("id"),
                    "project_uuid": item.get("name"),
                    "name": item.get("name"),
                }
            )
        edges = [
            {
                "source_id": e.get("source"),
                "target_id": e.get("target"),
                "anchor_package_name": e.get("anchor_package_name"),
                "consumer_row_count": e.get("weight"),
            }
            for e in leiden.get("edges") or []
        ]
        enriched_path = session_dir / "compile_dependency_graph_enriched.json"
        base = {}
        if enriched_path.is_file():
            base = json.loads(enriched_path.read_text(encoding="utf-8"))
        return {
            **base,
            "namespace": leiden.get("namespace") or base.get("namespace"),
            "nodes": base.get("nodes") or nodes,
            "edges": base.get("edges") or edges,
        }
    graph_path = session_dir / "compile_dependency_graph_enriched.json"
    if graph_path.is_file():
        return json.loads(graph_path.read_text(encoding="utf-8"))
    return json.loads(
        (session_dir / "compile_dependency_graph.json").read_text(encoding="utf-8")
    )


def run_graph_partition(
    flat_graph: dict[str, Any],
    *,
    options: PartitionOptions | None = None,
) -> tuple[dict[str, Any], PhaseValidation, dict[str, Any]]:
    try:
        import igraph as ig  # pyright: ignore[reportMissingTypeStubs]
        import leidenalg  # pyright: ignore[reportMissingTypeStubs]
    except ImportError:
        validation = PhaseValidation(
            phase="partition_graph",
            ok=False,
            checks=[
                PhaseCheck(
                    "igraph_leidenalg_installed",
                    False,
                    "Install optional extra: uv sync --extra graph",
                )
            ],
            generated_at=_utc_now(),
        )
        return {}, validation, {}

    opts = options or PartitionOptions()
    nodes = flat_graph.get("nodes") or []
    edges = flat_graph.get("edges") or []
    n = len(nodes)
    if n == 0:
        validation = PhaseValidation(
            phase="partition_graph",
            ok=False,
            checks=[PhaseCheck("node_count_gt_zero", False, "0 nodes")],
            generated_at=_utc_now(),
        )
        return {}, validation, {}

    graph_node_ids = [int(node["node_id"]) for node in nodes if "node_id" in node]
    id_to_idx = {nid: i for i, nid in enumerate(graph_node_ids)}

    g = ig.Graph(directed=True)
    g.add_vertices(len(graph_node_ids))
    e_pairs = []
    edge_index_map: list[int] = []
    for i, e in enumerate(edges):
        sid = int(e["source_id"])
        tid = int(e["target_id"])
        if sid in id_to_idx and tid in id_to_idx:
            e_pairs.append((id_to_idx[sid], id_to_idx[tid]))
            edge_index_map.append(i)
    if e_pairs:
        g.add_edges(e_pairs)
        ew = _edge_weights_for_partition(flat_graph, weight_field=opts.weight_field)
        if ew is not None:
            g.es["weight"] = [ew[i] for i in edge_index_map]

    if opts.component_min_size > 1:
        wcc = g.components(mode="weak")
        largest = max(wcc, key=len)
        if len(largest) < opts.component_min_size:
            validation = PhaseValidation(
                phase="partition_graph",
                ok=False,
                checks=[
                    PhaseCheck(
                        "largest_wcc_min_size",
                        False,
                        f"largest component size {len(largest)} < {opts.component_min_size}",
                    )
                ],
                generated_at=_utc_now(),
            )
            return {}, validation, {}

    vertex_weights = _partition_weights(flat_graph, weight_field=opts.weight_field)
    partition = leidenalg.find_partition(
        g,
        leidenalg.RBConfigurationVertexPartition,
        weights=vertex_weights,
        resolution_parameter=opts.resolution,
        n_iterations=opts.iterations,
        seed=opts.seed,
    )
    membership = {graph_node_ids[i]: int(m) for i, m in enumerate(partition.membership)}
    communities: dict[int, list[int]] = {}
    for node_id, comm in membership.items():
        communities.setdefault(comm, []).append(node_id)

    id_to_uuid = {int(n["node_id"]): str(n.get("project_uuid") or "") for n in nodes}
    community_rows = []
    for comm_id, comm_node_ids in sorted(communities.items()):
        uuids = [id_to_uuid[i] for i in sorted(comm_node_ids) if i in id_to_uuid]
        community_rows.append(
            {
                "community_id": comm_id,
                "node_ids": sorted(comm_node_ids),
                "project_uuids": uuids,
            }
        )

    payload = {
        "algorithm": "leiden",
        "schema": "endor.graph_partition.v1",
        "seed": opts.seed,
        "resolution": opts.resolution,
        "iterations": opts.iterations,
        "weight_field": opts.weight_field,
        "generated_at": _utc_now(),
        "node_count": len(graph_node_ids),
        "edge_count": len(e_pairs),
        "isolated_count": flat_graph.get("isolated_count", 0),
        "community_count": len(community_rows),
        "membership": {str(k): v for k, v in membership.items()},
        "communities": community_rows,
    }
    community_summary = _build_community_summary(flat_graph, community_rows)
    checks = [
        PhaseCheck(
            "partition_nonempty",
            len(membership) == len(graph_node_ids),
            f"{len(membership)} membership / {len(graph_node_ids)} nodes",
        ),
        PhaseCheck(
            "community_count_gt_zero",
            len(community_rows) > 0,
            f"{len(community_rows)} communities",
        ),
    ]
    validation = PhaseValidation(
        phase="partition_graph",
        ok=all(c.ok for c in checks),
        checks=checks,
        generated_at=_utc_now(),
    )
    return payload, validation, community_summary


def run_dependency_graph_pipeline(
    client: endorlabs.Client,
    *,
    namespace: str,
    context_dir: str | Path,
    max_pages: int | None = None,
    page_size: int = 500,
    dep_metadata_max_pages: int = 0,
    max_workers: int = 8,
    phases: set[PhaseName] | None = None,
    partition_options: PartitionOptions | None = None,
    cardinality_csv: Path | None = None,
    package_name_match: str | None = None,
    analytics_max_nodes: int = 5000,
    retry_fetch_errors: bool = False,
) -> Path:
    run_all = phases is None
    wanted = phases or {
        "discover_projects",
        "filter_git_repositories",
        "build_publisher_index",
        "collect_dependencies",
        "build_graph",
        "enrich_graph",
        "graph_analytics",
        "partition_graph",
    }
    out_dir = session_dir_for(context_dir, namespace)
    _configure_session_logging(out_dir)

    all_discover: list[dict[str, Any]] = []
    graph_project_rows: list[dict[str, Any]] = []
    project_set: set[str] = set()
    produced_by: dict[tuple[str, str], set[str]] = {}
    produced_name: dict[str, set[str]] = {}
    published_by_project: dict[str, list[dict[str, Any]]] = {}
    all_support: list[tuple[str, str, Any]] = []
    direct_edges: list[dict[str, Any]] = []

    if run_all or "discover_projects" in wanted:
        all_discover, val, project_in_scope = discover_projects(
            client,
            namespace=namespace,
            max_pages=max_pages,
            page_size=page_size,
            max_workers=max_workers,
        )
        _write_phase(
            out_dir,
            "discover_projects",
            {
                "namespace": namespace,
                "generated_at": val.generated_at,
                "list_mode": {"traverse": True, "concurrent": True},
                "in_scope_count": project_in_scope,
                "actual_row_count": len(all_discover),
                "project_count": len(all_discover),
                "projects": all_discover,
            },
            val,
        )
        if not val.ok:
            return out_dir
        if not run_all and wanted == {"discover_projects"}:
            return out_dir
    else:
        require_prior_phase(out_dir, "discover_projects")
        all_discover = _load_discover_rows(out_dir)

    if run_all or "filter_git_repositories" in wanted:
        require_prior_phase(out_dir, "discover_projects")
        graph_projects, registration_counts, val = run_filter_git_repositories(
            all_discover
        )
        graph_project_rows = graph_projects
        project_set = {str(r["uuid"]) for r in graph_project_rows if r.get("uuid")}
        binary_sample = [
            r
            for r in graph_projects
            if r.get("registration_type") == REGISTRATION_BINARY
        ][:50]
        _write_phase(
            out_dir,
            "filter_git_repositories",
            {
                "namespace": namespace,
                "generated_at": val.generated_at,
                "graph_project_count": len(graph_projects),
                "registration_counts": registration_counts,
                "graph_projects": graph_projects,
                "binary_component_sample": binary_sample,
            },
            val,
        )
        if not val.ok:
            return out_dir
    else:
        require_prior_phase(out_dir, "filter_git_repositories")
        graph_project_rows = _load_graph_project_rows(out_dir)
        project_set = {str(r["uuid"]) for r in graph_project_rows if r.get("uuid")}

    project_refs = _project_refs(graph_project_rows, namespace)

    if run_all or "build_publisher_index" in wanted:
        require_prior_phase(out_dir, "filter_git_repositories")
        (
            produced_by,
            produced_name,
            published_by_project,
            n_pv,
            val,
            pv_in_scope,
        ) = build_publisher_index(
            client,
            namespace=namespace,
            project_set=project_set,
            max_pages=max_pages,
            page_size=page_size,
            max_workers=max_workers,
        )
        _write_phase(
            out_dir,
            "build_publisher_index",
            {
                "namespace": namespace,
                "generated_at": val.generated_at,
                "list_mode": {"traverse": True, "concurrent": True},
                "context_filter": main_context_filter(),
                "in_scope_count": pv_in_scope,
                "package_version_count": n_pv,
                "distinct_package_names": len(produced_name),
                "published_by_project": published_by_project,
            },
            val,
        )
        if not val.ok:
            return out_dir

    def _refresh_publishers() -> None:
        nonlocal produced_by, produced_name, published_by_project
        produced_by, produced_name, published_by_project, _, _, _ = (
            build_publisher_index(
                client,
                namespace=namespace,
                project_set=project_set,
                max_pages=max_pages,
                page_size=page_size,
                max_workers=max_workers,
            )
        )

    def _refresh_support() -> None:
        nonlocal all_support
        _refresh_publishers()
        all_support, _, _, _, _, _, _ = collect_dependencies(
            client,
            projects=project_refs,
            project_set=project_set,
            produced_by=produced_by,
            produced_name=produced_name,
            dep_metadata_max_pages=dep_metadata_max_pages,
            page_size=page_size,
            max_workers=max_workers,
            session_dir=out_dir,
        )

    if run_all or "collect_dependencies" in wanted:
        require_prior_phase(out_dir, "build_publisher_index")
        if not produced_by:
            _refresh_publishers()
        collect_projects = project_refs
        corpus_append = False
        count_in_scope: int | None = None
        if retry_fetch_errors:
            failed_uuids = _load_collect_fetch_error_uuids(out_dir)
            collect_projects = [p for p in project_refs if p.uuid in failed_uuids]
            corpus_append = True
            prior_collect_path = out_dir / "phase_collect_dependencies.json"
            if prior_collect_path.is_file():
                prior_collect = json.loads(
                    prior_collect_path.read_text(encoding="utf-8")
                )
                count_in_scope = prior_collect.get("in_scope_count")
            LOGGER.info(
                "Retrying DependencyMetadata fetch for %d failed projects",
                len(collect_projects),
            )
        (
            all_support,
            total_rows,
            val,
            truncated_projects,
            dm_in_scope,
            corpus_records,
            fetch_errors,
        ) = collect_dependencies(
            client,
            projects=collect_projects,
            project_set=project_set,
            produced_by=produced_by,
            produced_name=produced_name,
            dep_metadata_max_pages=dep_metadata_max_pages,
            page_size=page_size,
            max_workers=max_workers,
            session_dir=out_dir,
            corpus_append=corpus_append,
            count_in_scope=count_in_scope,
        )
        corpus_path = out_dir / "dependency_corpus.jsonl"
        corpus_record_count = len(corpus_records)
        if corpus_path.is_file():
            with corpus_path.open(encoding="utf-8") as handle:
                corpus_record_count = sum(1 for _ in handle)
        if corpus_record_count:
            _write_corpus_manifest(
                out_dir,
                namespace=namespace,
                record_count=corpus_record_count,
            )
        _write_collect_fetch_errors(out_dir, fetch_errors)
        reported_in_scope = (
            count_in_scope if count_in_scope is not None else dm_in_scope
        )
        _write_phase(
            out_dir,
            "collect_dependencies",
            {
                "namespace": namespace,
                "generated_at": val.generated_at,
                "in_scope_count": reported_in_scope,
                "actual_row_count": total_rows,
                "dependency_row_count": total_rows,
                "corpus_record_count": corpus_record_count,
                "supporting_tuple_count": len(all_support),
                "direct_only": True,
                "dep_metadata_truncated_project_count": len(truncated_projects),
                "dep_metadata_truncated_project_sample": truncated_projects[:25],
                "fetch_error_count": len(fetch_errors),
                "fetch_error_sample": fetch_errors[:25],
                "retry_fetch_errors": retry_fetch_errors,
            },
            val,
        )
        if all_support:
            direct_edges = aggregate_compile_dependency_edges(all_support)
            if (
                retry_fetch_errors
                and (out_dir / "collected_direct_edges.json").is_file()
            ):
                prior = _load_collected_direct_edges(out_dir) or []

                def _edge_key(edge: dict[str, Any]) -> tuple[Any, Any, Any]:
                    return (
                        edge.get("source_id"),
                        edge.get("target_id"),
                        edge.get("anchor_package_name"),
                    )

                merged = {_edge_key(e): e for e in prior}
                for edge in direct_edges:
                    merged[_edge_key(edge)] = edge
                direct_edges = list(merged.values())
            _save_collected_direct_edges(
                out_dir,
                namespace=namespace,
                edges=direct_edges,
                supporting_tuple_count=len(all_support),
            )
        if not val.ok:
            return out_dir

    if run_all or "build_graph" in wanted:
        require_prior_phase(out_dir, "collect_dependencies")
        loaded = _load_collected_direct_edges(out_dir)
        if loaded is None:
            if not all_support:
                _refresh_support()
            direct_edges = aggregate_compile_dependency_edges(all_support)
        else:
            direct_edges = loaded
        if not published_by_project:
            pub_path = out_dir / "phase_build_publisher_index.json"
            pub_data = json.loads(pub_path.read_text(encoding="utf-8"))
            raw_pub = pub_data.get("published_by_project") or {}
            if isinstance(raw_pub, dict):
                published_by_project = {
                    str(k): v for k, v in raw_pub.items() if isinstance(v, list)
                }
        flat = build_graph_document(
            namespace=namespace,
            projects=graph_project_rows,
            aggregated_edges=direct_edges,
            published_by_project=published_by_project,
        )
        checks = [
            PhaseCheck(
                "graph_built",
                flat["node_count"] > 0,
                (
                    f"{flat['edge_count']} edges, {flat['node_count']} nodes, "
                    f"{flat['isolated_count']} isolated"
                ),
            ),
        ]
        val = PhaseValidation(
            phase="build_graph",
            ok=all(c.ok for c in checks),
            checks=checks,
            generated_at=_utc_now(),
        )
        _write_phase(out_dir, "build_graph", flat, val)
        write_json(
            str(out_dir / "compile_dependency_graph.json"),
            flat,
            base_dir=out_dir,
        )
        rankings = compute_publisher_rankings(flat)
        write_json(
            str(out_dir / "publisher_rankings.json"),
            rankings,
            base_dir=out_dir,
        )
        if not val.ok:
            return out_dir

    if run_all or "enrich_graph" in wanted:
        require_prior_phase(out_dir, "build_graph")
        enrich_result = run_enrich_graph_phase(out_dir, cardinality_csv=cardinality_csv)
        checks = [
            PhaseCheck(
                "enriched_graph_written",
                bool(enrich_result.enriched.get("nodes")),
                f"{len(enrich_result.enriched.get('nodes') or [])} nodes",
            ),
        ]
        val = PhaseValidation(
            phase="enrich_graph",
            ok=all(c.ok for c in checks),
            checks=checks,
            generated_at=_utc_now(),
        )
        _write_phase(
            out_dir,
            "enrich_graph",
            {
                "namespace": namespace,
                "generated_at": val.generated_at,
                "schema": enrich_result.enriched.get("schema"),
                "node_count": len(enrich_result.enriched.get("nodes") or []),
                "edge_count": len(enrich_result.enriched.get("edges") or []),
            },
            val,
        )

    if run_all or "graph_analytics" in wanted:
        require_prior_phase(out_dir, "build_graph")
        metrics = run_graph_analytics_phase(
            out_dir,
            package_name_match=package_name_match,
            max_betweenness_nodes=analytics_max_nodes,
        )
        checks = [
            PhaseCheck(
                "metrics_written",
                bool(metrics.get("centrality")),
                "graph_metrics.json",
            ),
        ]
        val = PhaseValidation(
            phase="graph_analytics",
            ok=all(c.ok for c in checks),
            checks=checks,
            generated_at=_utc_now(),
        )
        _write_phase(
            out_dir,
            "graph_analytics",
            {
                "namespace": namespace,
                "generated_at": val.generated_at,
                "node_count": metrics.get("node_count"),
                "edge_count": metrics.get("edge_count"),
            },
            val,
        )

    if run_all or "partition_graph" in wanted:
        require_prior_phase(out_dir, "build_graph")
        flat = _load_partition_graph_input(out_dir)
        partition_payload, val, community_summary = run_graph_partition(
            flat, options=partition_options
        )
        _write_phase(out_dir, "partition_graph", partition_payload, val)
        if val.ok:
            write_json(
                str(out_dir / "graph_partition.json"),
                partition_payload,
                base_dir=out_dir,
            )
            write_json(
                str(out_dir / "community_summary.json"),
                community_summary,
                base_dir=out_dir,
            )

    return out_dir


PHASE_CHOICES: tuple[str, ...] = (
    "all",
    "discover_projects",
    "filter_git_repositories",
    "build_publisher_index",
    "collect_dependencies",
    "build_graph",
    "enrich_graph",
    "graph_analytics",
    "partition_graph",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Estate compile-dependency graph: direct imports anchored on "
            "package_name, main context, phased session artifacts."
        )
    )
    p.add_argument(
        "--tenant",
        required=True,
        help="Client tenant for endorlabs.Client.",
    )
    p.add_argument(
        "--namespace",
        action="append",
        required=True,
        dest="namespaces",
        metavar="NAMESPACE",
        help="Estate namespace root (repeat per tenant).",
    )
    p.add_argument(
        "--context-dir",
        default=".endorlabs-context",
        help="Context root; output under <context-dir>/session/<slug>/.",
    )
    p.add_argument(
        "--phase",
        choices=PHASE_CHOICES,
        default="all",
        help="Run one phase or all (default: all).",
    )
    p.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Max pages for Project/PackageVersion lists (0 = unlimited).",
    )
    p.add_argument("--page-size", type=int, default=500, help="List page size.")
    p.add_argument(
        "--dep-metadata-max-pages",
        type=int,
        default=0,
        help="Max pages per project for DependencyMetadata (0 = unlimited).",
    )
    p.add_argument(
        "--max-workers",
        type=int,
        default=8,
        help="Parallel workers for per-project dependency fetch.",
    )
    p.add_argument(
        "--partition-resolution",
        type=float,
        default=1.0,
        help="Leiden resolution_parameter (default 1.0).",
    )
    p.add_argument(
        "--partition-iterations",
        type=int,
        default=10,
        help="Leiden n_iterations (default 10).",
    )
    p.add_argument(
        "--partition-weight-field",
        choices=["none", "consumer_row_count", "inbound_rank"],
        default="none",
        help="Edge/vertex weight source for Leiden.",
    )
    p.add_argument(
        "--partition-component-min-size",
        type=int,
        default=1,
        help="Skip Leiden when largest WCC is smaller than N.",
    )
    p.add_argument(
        "--cardinality-csv",
        default=None,
        help="Optional version_cardinality.csv from analytics export for enrich join.",
    )
    p.add_argument(
        "--package-name-match",
        default=None,
        help="Optional package coordinate for package_subgraph.json in graph_analytics.",
    )
    p.add_argument(
        "--analytics-max-nodes",
        type=int,
        default=5000,
        help="Cap graph size for expensive betweenness (default 5000).",
    )
    p.add_argument(
        "--retry-fetch-errors",
        action="store_true",
        help=(
            "Re-fetch DependencyMetadata only for projects in collect_fetch_errors.json; "
            "append to dependency_corpus.jsonl."
        ),
    )
    return p.parse_args(argv)


def _phase_set(phase: str) -> set[PhaseName] | None:
    if phase == "all":
        return None
    return {phase}  # type: ignore[return-value]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    phases = _phase_set(args.phase)
    context_dir = Path(args.context_dir)
    exit_code = 0

    client = endorlabs.Client(tenant=args.tenant)
    try:
        for namespace in args.namespaces:
            slug = namespace_slug(namespace)
            LOGGER.info(
                "Compile dependency graph namespace=%s slug=%s phase=%s",
                namespace,
                slug,
                args.phase,
            )
            partition_opts = PartitionOptions(
                resolution=args.partition_resolution,
                iterations=args.partition_iterations,
                weight_field=args.partition_weight_field,
                component_min_size=args.partition_component_min_size,
            )
            cardinality_path = (
                Path(args.cardinality_csv) if args.cardinality_csv else None
            )
            out = run_dependency_graph_pipeline(
                client,
                namespace=namespace,
                context_dir=context_dir,
                max_pages=resolve_max_pages(args.max_pages),
                page_size=args.page_size,
                dep_metadata_max_pages=args.dep_metadata_max_pages,
                max_workers=args.max_workers,
                phases=phases,
                partition_options=partition_opts,
                cardinality_csv=cardinality_path,
                package_name_match=args.package_name_match,
                analytics_max_nodes=args.analytics_max_nodes,
                retry_fetch_errors=args.retry_fetch_errors,
            )
            final_phase = args.phase if args.phase != "all" else "partition_graph"
            val_path = out / f"phase_{final_phase}_validation.json"
            if not val_path.is_file() and args.phase == "all":
                for phase in reversed(PHASE_CHOICES):
                    if phase == "all":
                        continue
                    candidate = out / f"phase_{phase}_validation.json"
                    if candidate.is_file():
                        val_path = candidate
                        break
            if val_path.is_file():
                val = json.loads(val_path.read_text(encoding="utf-8"))
                if not val.get("ok"):
                    LOGGER.error(
                        "Validation failed for %s; see %s",
                        namespace,
                        val_path,
                    )
                    exit_code = 1
            LOGGER.info("Session output: %s", session_dir_for(context_dir, namespace))
    finally:
        client.close()

    return exit_code


# Public aliases for collect-strategy spike and tests.
ProjectRef = _ProjectRef
project_rows_from_models = _project_rows_from_models
project_refs = _project_refs

if __name__ == "__main__":
    raise SystemExit(main())
