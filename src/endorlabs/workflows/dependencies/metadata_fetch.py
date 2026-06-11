"""DependencyMetadata list fetch and summarization."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from endorlabs import Client


def retrieve_dep_metadata_full(
    client: Client,
    project_namespace: str,
    project_uuid: str,
    max_pages: int | None = None,
    *,
    page_size: int = 500,
) -> tuple[list[dict[str, Any]], str, bool]:
    """Retrieve all DependencyMetadata rows for a project.

    Tries the project's namespace first, then falls back to ``"oss"``.
    Returns ``(rows, source_namespace, truncated)``.
    """
    from endorlabs.workflows.estate.collect.bounds import (
        is_list_truncated,
        resolve_max_pages,
    )

    resolved_pages = resolve_max_pages(max_pages)
    dep_filter = f'spec.importer_data.project_uuid=="{project_uuid}"'
    for ns in [project_namespace, "oss"]:
        objects = client.DependencyMetadata.list(
            namespace=ns,
            filter=dep_filter,
            max_pages=resolved_pages,
            page_size=page_size,
        )
        if objects:
            rows = [
                item if isinstance(item, dict) else item.model_dump(mode="json")
                for item in objects
            ]
            truncated = is_list_truncated(
                len(objects),
                max_pages=resolved_pages,
                page_size=page_size,
            )
            return rows, ns, truncated
    return [], "", False


def summarize_dep_metadata(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a human-readable summary from raw DependencyMetadata rows."""
    stats: dict[str, Any] = {
        "total": len(rows),
        "direct": 0,
        "transitive": 0,
        "reachable": 0,
        "unreachable": 0,
        "unknown_reachability": 0,
        "by_ecosystem": defaultdict(int),
        "by_scope": defaultdict(int),
    }
    for row in rows:
        spec = row.get("spec", {}) or {}
        dd = spec.get("dependency_data", {}) or {}
        if dd.get("direct", False):
            stats["direct"] += 1
        else:
            stats["transitive"] += 1
        reach = dd.get("reachable", "") or dd.get("reachability", "")
        if isinstance(reach, str):
            if "UNREACHABLE" in reach:
                stats["unreachable"] += 1
            elif "REACHABLE" in reach:
                stats["reachable"] += 1
            else:
                stats["unknown_reachability"] += 1
        eco = dd.get("ecosystem", "?") or "?"
        stats["by_ecosystem"][eco] += 1
        scope = dd.get("scope", "?") or "?"
        stats["by_scope"][scope] += 1
    stats["by_ecosystem"] = dict(stats["by_ecosystem"])
    stats["by_scope"] = dict(stats["by_scope"])
    return stats
