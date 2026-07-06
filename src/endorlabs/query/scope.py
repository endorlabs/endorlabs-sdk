"""Query POST scope: wire namespace plus optional root key batch."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .execute import project_namespace, project_uuid

if TYPE_CHECKING:
    from .topology import TopologySnapshot


@dataclass(frozen=True, slots=True)
class QueryScope:
    """One Query POST unit: URL namespace and optional root ``uuid`` keys."""

    namespace: str
    keys: tuple[str, ...] = ()


def scopes_from_projects(projects: list[Any]) -> list[QueryScope]:
    """Group project rows into leaf-namespace scopes with UUID key batches."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in projects:
        ns = project_namespace(row)
        uid = project_uuid(row)
        if not ns or not uid:
            continue
        grouped[ns].append(uid)
    return [
        QueryScope(namespace=ns, keys=tuple(sorted(set(uuids))))
        for ns, uuids in sorted(grouped.items())
    ]


def query_scopes_from_topology(topology: TopologySnapshot) -> list[QueryScope]:
    """Build query-plane scopes from a topology snapshot."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for proj in topology.projects:
        grouped[proj.namespace].append(proj.uuid)
    return [
        QueryScope(namespace=ns, keys=tuple(sorted(set(uuids))))
        for ns, uuids in sorted(grouped.items())
    ]
