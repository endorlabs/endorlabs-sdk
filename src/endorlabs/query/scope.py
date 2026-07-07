"""Query POST scope: wire namespace plus optional root key batch."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .row_fields import project_namespace, project_uuid


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
