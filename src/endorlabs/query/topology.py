"""Bounded topology discovery for Query vs facade routing."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Literal, cast

from .row_fields import project_namespace, project_uuid

Archetype = Literal[
    "single_repo",
    "monorepo_hub",
    "managed_platform",
    "estate_sprawl",
    "mixed",
]

PROJECT_DISCOVERY_MASK = "uuid,meta.name,tenant_meta.namespace"
PAGINATION_THRESHOLD = 500


@dataclass(frozen=True, slots=True)
class DiscoveredProject:
    """One project row from bounded discovery."""

    uuid: str
    name: str
    namespace: str


@dataclass
class NamespaceGeometry:
    """Per-leaf-namespace geometry for routing."""

    namespace: str
    project_count: int
    depth: int
    estimated_pages: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize namespace geometry for artifacts."""
        return {
            "namespace": self.namespace,
            "project_count": self.project_count,
            "depth": self.depth,
            "estimated_pages": self.estimated_pages,
        }


@dataclass
class TopologySnapshot:
    """Client-side estate geometry from bounded ``Project.list``."""

    tenant: str
    project_count: int
    namespace_count: int
    max_projects_per_namespace: int
    archetype: Archetype
    projects: list[DiscoveredProject] = field(default_factory=list[DiscoveredProject])
    namespace_geometry: list[NamespaceGeometry] = field(
        default_factory=list[NamespaceGeometry]
    )
    duplicate_name_groups: list[dict[str, Any]] = field(
        default_factory=list[dict[str, Any]]
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize topology snapshot for artifacts."""
        return {
            "tenant": self.tenant,
            "project_count": self.project_count,
            "namespace_count": self.namespace_count,
            "max_projects_per_namespace": self.max_projects_per_namespace,
            "archetype": self.archetype,
            "namespace_geometry": [g.to_dict() for g in self.namespace_geometry],
            "duplicate_name_groups": self.duplicate_name_groups,
        }

    def project_shards(self) -> list[Any]:
        """List-plane parallel shards derived from discovered projects."""
        from endorlabs.tools.list_sharding import topology_to_project_shards

        return topology_to_project_shards(self, fallback_ns=self.tenant)

    def query_scopes(self) -> list[Any]:
        """Query-plane POST scopes derived from discovered projects."""
        return query_scopes_from_topology(self)


def query_scopes_from_topology(topology: TopologySnapshot) -> list[Any]:
    """Build query-plane scopes from a topology snapshot."""
    from .scope import QueryScope

    grouped: dict[str, list[str]] = defaultdict(list)
    for proj in topology.projects:
        grouped[proj.namespace].append(proj.uuid)
    scopes: list[QueryScope] = [
        QueryScope(namespace=ns, keys=tuple(sorted(set(uuids))))
        for ns, uuids in sorted(grouped.items())
    ]
    return scopes


def infer_archetype(
    project_count: int,
    namespace_count: int,
    max_projects_per_namespace: int,
) -> Archetype:
    """Classify tenant layout from discovery signals."""
    if project_count <= 1:
        return "single_repo"
    if namespace_count <= 3 and max_projects_per_namespace >= PAGINATION_THRESHOLD:
        return "monorepo_hub"
    if namespace_count >= 50:
        return "estate_sprawl"
    if namespace_count >= 10:
        return "managed_platform"
    return "mixed"


def _project_row(row: Any, fallback_ns: str) -> DiscoveredProject | None:
    if isinstance(row, dict):
        row_dict = cast("dict[str, Any]", row)
        uuid = str(row_dict.get("uuid") or "")
        meta_raw = row_dict.get("meta")
        meta = cast("dict[str, Any]", meta_raw) if isinstance(meta_raw, dict) else {}
        name = meta.get("name")
        tm_raw = row_dict.get("tenant_meta")
        tm = cast("dict[str, Any]", tm_raw) if isinstance(tm_raw, dict) else {}
        ns = tm.get("namespace")
    else:
        uuid = project_uuid(row)
        meta = getattr(row, "meta", None)
        name = getattr(meta, "name", None) if meta else None
        ns = project_namespace(row)
    if not uuid:
        return None
    wire_ns = str(ns) if ns else fallback_ns
    return DiscoveredProject(
        uuid=uuid,
        name=str(name) if name else uuid,
        namespace=wire_ns,
    )


def _dedupe_projects(rows: list[Any], fallback_ns: str) -> list[DiscoveredProject]:
    by_uuid: dict[str, DiscoveredProject] = {}
    for row in rows:
        ref = _project_row(row, fallback_ns)
        if ref is None:
            continue
        existing = by_uuid.get(ref.uuid)
        if existing is None or ref.namespace.count(".") > existing.namespace.count("."):
            by_uuid[ref.uuid] = ref
    return sorted(by_uuid.values(), key=lambda p: p.uuid)


def _duplicate_name_groups(
    projects: list[DiscoveredProject],
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    by_name: dict[str, set[str]] = defaultdict(set)
    for proj in projects:
        by_name[proj.name].add(proj.namespace)
    dups: list[dict[str, Any]] = [
        {
            "meta.name": name,
            "namespace_count": len(namespaces),
            "namespaces": sorted(namespaces),
        }
        for name, namespaces in by_name.items()
        if len(namespaces) > 1
    ]
    return sorted(dups, key=lambda d: -int(d["namespace_count"]))[:limit]


def _namespace_geometry(projects: list[DiscoveredProject]) -> list[NamespaceGeometry]:
    grouped: dict[str, list[DiscoveredProject]] = defaultdict(list)
    for proj in projects:
        grouped[proj.namespace].append(proj)
    geometry: list[NamespaceGeometry] = []
    for ns, refs in sorted(grouped.items()):
        count = len(refs)
        depth = ns.count(".")
        pages = max(1, (count + PAGINATION_THRESHOLD - 1) // PAGINATION_THRESHOLD)
        geometry.append(
            NamespaceGeometry(
                namespace=ns,
                project_count=count,
                depth=depth,
                estimated_pages=pages,
            )
        )
    return geometry


def discover_topology(
    client: Any,
    namespace: str,
    *,
    traverse: bool = True,
    max_pages: int | None = None,
    exclude_sbom: bool = False,
) -> TopologySnapshot:
    """Discover project geometry via lean ``Project.list`` (no ProjectSummary)."""
    mask = PROJECT_DISCOVERY_MASK
    if exclude_sbom:
        mask = f"{mask},spec.sbom"
    list_kwargs: dict[str, Any] = {
        "namespace": namespace,
        "traverse": traverse,
        "mask": mask,
    }
    if max_pages is not None:
        list_kwargs["max_pages"] = max_pages
    rows = client.Project.list(**list_kwargs)
    if exclude_sbom:
        rows = [row for row in rows if not client.Project.is_sbom(row)]
    projects = _dedupe_projects(list(rows), namespace)
    geometry = _namespace_geometry(projects)
    max_ns = max((g.project_count for g in geometry), default=0)
    archetype = infer_archetype(len(projects), len(geometry), max_ns)
    return TopologySnapshot(
        tenant=namespace,
        project_count=len(projects),
        namespace_count=len(geometry),
        max_projects_per_namespace=max_ns,
        archetype=archetype,
        projects=projects,
        namespace_geometry=geometry,
        duplicate_name_groups=_duplicate_name_groups(projects),
    )
