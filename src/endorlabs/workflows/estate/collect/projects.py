"""Discover estate projects into workspace ``data/project.jsonl``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.estate.collect.bounds import (
    count_for_progress,
    is_list_truncated,
    truncation_message,
)
from endorlabs.workflows.estate.contracts import RESOURCE_PROJECT
from endorlabs.workflows.estate.filters.masks import PROJECT_LIST_MASK
from endorlabs.workflows.estate.workspace.paths import resource_path

if TYPE_CHECKING:
    from endorlabs import Client

LOGGER = get_resource_logger(__name__)


def _project_row(project: Any, fallback_ns: str) -> dict[str, Any]:
    if isinstance(project, dict):
        tenant_meta = project.get("tenant_meta") or {}
        meta = project.get("meta") or {}
        ns = tenant_meta.get("namespace") or fallback_ns
        return {
            "uuid": project.get("uuid"),
            "meta": {
                "name": meta.get("name"),
                "tags": meta.get("tags"),
            },
            "tenant_meta": {"namespace": ns},
        }
    tenant_meta = getattr(project, "tenant_meta", None)
    ns = getattr(tenant_meta, "namespace", None) if tenant_meta else fallback_ns
    meta = getattr(project, "meta", None)
    return {
        "uuid": getattr(project, "uuid", None),
        "meta": {
            "name": getattr(meta, "name", None) if meta else None,
            "tags": getattr(meta, "tags", None) if meta else None,
        },
        "tenant_meta": {"namespace": ns},
    }


def collect_project_resource(
    client: Client,
    *,
    namespace: str,
    workspace_root: Path,
    max_pages: int | None = None,
    page_size: int = 500,
    max_workers: int = 10,
) -> tuple[list[dict[str, Any]], int | None]:
    """List projects with traverse and write ``data/project.jsonl``."""
    in_scope = count_for_progress(
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
    if is_list_truncated(len(projects), max_pages=max_pages, page_size=page_size):
        LOGGER.warning(
            "%s",
            truncation_message(
                resource="Project",
                scope=f"namespace={namespace} traverse=true",
                row_count=len(projects),
                max_pages=max_pages,
                page_size=page_size,
            ),
        )
    rows = [_project_row(project, namespace) for project in projects]
    out_path = resource_path(workspace_root, RESOURCE_PROJECT)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")
    return rows, in_scope


def load_project_records(workspace_root: Path) -> list[dict[str, Any]]:
    path = resource_path(workspace_root, RESOURCE_PROJECT)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows
