"""Resolve a Project from tenant root when direct GET in a namespace returns 404."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from endorlabs.workflows.estate.collect.bounds import (
    is_list_truncated,
    resolve_max_pages,
)

if TYPE_CHECKING:
    from endorlabs import Client


def is_hex_project_id(value: str) -> bool:
    """Return whether *value* is a 24-character lowercase hex project UUID."""
    return len(value) == 24 and all(c in "0123456789abcdef" for c in value.lower())


def resolve_project(
    client: Client,
    namespace: str,
    project: str,
    warnings: list[str],
) -> Any:
    """Resolve a project by UUID (with traverse fallback) or by name (lookup)."""
    return client.Project.resolve(project, namespace=namespace, warnings_out=warnings)


def search_projects_by_name_or_uuid(
    client: Client,
    *,
    namespace: str,
    query: str,
    max_pages: int = 0,
    page_size: int = 100,
    warnings: list[str] | None = None,
) -> list[Any]:
    """Search projects by UUID or case-insensitive name substring."""
    needle = query.strip().lower()
    list_max_pages = resolve_max_pages(max_pages)
    projects = client.Project.list(
        namespace=namespace,
        traverse=True,
        max_pages=list_max_pages,
        page_size=page_size,
    )
    if is_list_truncated(len(projects), max_pages=list_max_pages, page_size=page_size):
        msg = (
            f"Project search list may be truncated at {len(projects)} rows; "
            "matches beyond the cap are invisible — use max_pages=0."
        )
        if warnings is not None:
            warnings.append(msg)
    out: list[Any] = []
    for project in projects:
        pname = (
            project.meta.name if project.meta and project.meta.name else ""
        ).lower()
        puid = str(project.uuid).lower() if project.uuid else ""
        if needle in pname or needle in puid:
            out.append(project)
    return out
