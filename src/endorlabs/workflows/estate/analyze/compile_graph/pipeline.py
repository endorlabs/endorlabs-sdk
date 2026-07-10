#!/usr/bin/env python3
"""Estate compile-dependency graph helpers (main context).

The stitched graph is **directed** (consumer → publisher on direct compile imports).
It is **not** guaranteed acyclic: mutual internal dependencies can form cycles.
Multi-hop reachability is a post-build query on ``compile_dependency_graph.json``;
this pipeline does not precompute indirect paths.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from endorlabs.filters import main_context_filter
from endorlabs.query import OutputShape, preflight_count
from endorlabs.tools.list_bounds import (
    count_for_progress,
    format_progress,
    is_list_truncated,
    truncation_message,
)
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.dependencies.coordinates import parse_dep_name
from endorlabs.workflows.estate.analyze.project_map.core import (
    add_producer_indices,
    aggregate_package_anchored_edges,
)
from endorlabs.workflows.estate.contracts.ir_artifacts import (
    COMPILE_DEPENDENCY_GRAPH_SCHEMA,
    PRODUCER_RANKINGS_SCHEMA,
)
from endorlabs.workflows.estate.filters.masks import PV_PUBLISHER_LIST_MASK

if TYPE_CHECKING:
    from endorlabs import Client

LOGGER = get_resource_logger(__name__)

RegistrationType = Literal["git_repository", "binary_component"]
REGISTRATION_GIT: RegistrationType = "git_repository"
REGISTRATION_BINARY: RegistrationType = "binary_component"
GIT_URL_NAME_RE = re.compile(r"^(https?://|git@)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class _ProjectRef:
    uuid: str
    namespace: str


def namespace_slug(namespace: str) -> str:
    cleaned = namespace.strip().rstrip(".")
    if not cleaned:
        return "unknown"
    return cleaned.replace(".", "_")


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
        linking_pkg = str(raw.get("linking_package_name") or "")
        if not linking_pkg or fr not in uuid_to_node or to not in uuid_to_node:
            continue
        importer_id = uuid_to_node[fr]
        producer_id = uuid_to_node[to]
        if importer_id == producer_id:
            continue
        key = (importer_id, producer_id, linking_pkg)
        if key not in merged:
            merged[key] = {
                "importer_vertex_id": importer_id,
                "producer_vertex_id": producer_id,
                "linking_package_name": linking_pkg,
                "importer_uuids": set(),
                "producer_uuids": set(),
                "package_version": raw.get("package_version"),
                "match_tier": raw.get("match_tier"),
                "visibility": raw.get("visibility"),
            }
        row = merged[key]
        row["importer_uuids"].add(fr)
        row["producer_uuids"].add(to)
        row["match_tier"] = _stronger_match_tier(
            row.get("match_tier"),
            raw.get("match_tier"),
        )
        if raw.get("package_version"):
            row["package_version"] = raw.get("package_version")

    edges: list[dict[str, Any]] = []
    for row in merged.values():
        importer_uuids = sorted(row["importer_uuids"])
        producer_uuids = sorted(row["producer_uuids"])
        edges.append(
            {
                "importer_vertex_id": row["importer_vertex_id"],
                "producer_vertex_id": row["producer_vertex_id"],
                "importer_uuid": importer_uuids[0],
                "producer_uuid": producer_uuids[0],
                "importer_uuids": importer_uuids,
                "producer_uuids": producer_uuids,
                "linking_package_name": row["linking_package_name"],
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
        importer_id = int(edge["importer_vertex_id"])
        producer_id = int(edge["producer_vertex_id"])
        out_degree[importer_id] = out_degree.get(importer_id, 0) + 1
        in_degree[producer_id] = in_degree.get(producer_id, 0) + 1
        importer_node = node_by_id.get(importer_id, {})
        producer_node = node_by_id.get(producer_id, {})
        entry = {
            "linking_package_name": edge.get("linking_package_name"),
            "package_version": edge.get("package_version"),
            "producer_vertex_id": producer_id,
            "producer_name": producer_node.get("name"),
            "match_tier": edge.get("match_tier"),
            "visibility": edge.get("visibility"),
        }
        importer_node.setdefault("direct_imports", []).append(entry)
        producer_node.setdefault("imported_by", []).append(
            {
                "linking_package_name": edge.get("linking_package_name"),
                "package_version": edge.get("package_version"),
                "importer_vertex_id": importer_id,
                "importer_name": importer_node.get("name"),
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


def compute_producer_rankings(
    import_graph: dict[str, Any],
    *,
    top_n: int = 50,
) -> dict[str, Any]:
    nodes = import_graph.get("nodes") or []
    edges = import_graph.get("edges") or []
    node_by_id = {int(n["node_id"]): n for n in nodes if "node_id" in n}

    inbound_imports: dict[int, int] = {}
    importer_nodes: dict[int, set[int]] = {}
    linking_packages: dict[int, set[str]] = {}

    for edge in edges:
        importer_id = int(edge["importer_vertex_id"])
        producer_id = int(edge["producer_vertex_id"])
        inbound_imports[producer_id] = inbound_imports.get(producer_id, 0) + 1
        importer_nodes.setdefault(producer_id, set()).add(importer_id)
        pkg = edge.get("linking_package_name")
        if pkg:
            linking_packages.setdefault(producer_id, set()).add(str(pkg))

    sorted_producers = sorted(
        inbound_imports.items(), key=lambda item: (-item[1], item[0])
    )
    rankings: list[dict[str, Any]] = []
    for rank, (nid, import_count) in enumerate(sorted_producers[:top_n], start=1):
        node = node_by_id.get(nid, {})
        pkgs = sorted(linking_packages.get(nid, set()))
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
                "importer_count": len(importer_nodes.get(nid, set())),
                "inbound_import_count": import_count,
                "sample_linking_packages": pkgs[:10],
                "linking_package_count": len(pkgs),
            }
        )

    return {
        "schema": PRODUCER_RANKINGS_SCHEMA,
        "namespace": import_graph.get("namespace"),
        "generated_at": _utc_now(),
        "total_nodes": len(nodes),
        "isolated_count": import_graph.get("isolated_count", 0),
        "project_registration_count": import_graph.get("project_registration_count"),
        "total_edges": len(edges),
        "producers_with_importers": len(inbound_imports),
        "top_n": top_n,
        "rankings": rankings,
    }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


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


def run_filter_git_repositories(
    project_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[RegistrationType, int]]:
    """Classify projects and return graph nodes plus registration counts."""
    return classify_project_registrations(project_rows)


def build_publisher_index(
    client: Client,
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
]:
    pv_filter = main_context_filter()
    in_scope_count: int | None = None
    if project_set:
        try:
            topology = client.Query.Project.discover(namespace, traverse=True)
            scoped = [p for p in topology.projects if p.uuid in project_set]
            in_scope_count = preflight_count(
                client,
                plane="query",
                projects=scoped,
                shape=OutputShape.COUNT_BY_PROJECT,
                logger=LOGGER,
            )
        except Exception as exc:
            LOGGER.debug("Query PV preflight unavailable: %s", exc)
    if in_scope_count is None:
        in_scope_count = count_for_progress(
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
    LOGGER.info(
        "%s",
        format_progress(
            "PackageVersion index",
            n_pv,
            in_scope_count,
            extra=f"{len(pvs)} listed rows",
        ),
    )
    return produced_by, produced_name, published_by_project, n_pv


# Public aliases for collect-strategy spike and tests.
ProjectRef = _ProjectRef
project_rows_from_models = _project_rows_from_models
project_refs = _project_refs
