"""Resolve a Project from tenant root when direct GET in a namespace returns 404."""

from __future__ import annotations

from typing import Any

import endorlabs
from endorlabs import F
from endorlabs.core.exceptions import NotFoundError


def is_hex_project_id(value: str) -> bool:
    return len(value) == 24 and all(c in "0123456789abcdef" for c in value.lower())


def resolve_project(
    client: endorlabs.Client,
    namespace: str,
    project: str,
    warnings: list[str],
) -> Any:
    """Resolve a project by UUID (with traverse fallback) or by name (lookup)."""
    if is_hex_project_id(project):
        try:
            return client.Project.get(project, namespace=namespace)
        except NotFoundError:
            matches = client.Project.list(
                namespace=namespace,
                filter=F("uuid") == project,
                traverse=True,
                max_pages=1,
                page_size=5,
            )
            if not matches:
                raise
            warnings.append(
                f"Project {project!r} is not in namespace {namespace!r}; "
                "resolved the same UUID via list(traverse=True)."
            )
            return matches[0]
    return client.Project.lookup(name=project, namespace=namespace, traverse=True)


def search_projects_by_name_or_uuid(
    client: endorlabs.Client,
    *,
    namespace: str,
    query: str,
    max_pages: int = 50,
    page_size: int = 100,
) -> list[Any]:
    """Search projects by UUID or case-insensitive name substring."""
    needle = query.strip().lower()
    projects = client.Project.list(
        namespace=namespace,
        traverse=True,
        max_pages=max_pages,
        page_size=page_size,
    )
    out: list[Any] = []
    for project in projects:
        pname = (
            project.meta.name if project.meta and project.meta.name else ""
        ).lower()
        puid = str(project.uuid).lower() if project.uuid else ""
        if needle in pname or needle in puid:
            out.append(project)
    return out
