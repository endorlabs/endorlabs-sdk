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
