"""Bounded scan-result window acquisition for host injection (SDK-006).

``acquire_scan_results`` fetches via an injected ``Client`` and returns typed
evidence without filesystem writes. CLI adapters call this then write JSON.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.troubleshooting_scans.common import (
    object_to_dict,
    parallel_collect_for_projects,
    scan_result_metrics,
)
from endorlabs.workflows.wire_access import dict_str, nested_str

if TYPE_CHECKING:
    from endorlabs.client_surface import Client
    from endorlabs.tools.list_sharding import ProjectShard


def _empty_list() -> list[dict[str, Any]]:
    return []


@dataclass
class ScanResultsEvidence(WorkflowResult):
    """Typed scan-result window; no artifact paths."""

    query_namespace: str = ""
    project_count: int = 0
    scan_results: list[dict[str, Any]] = field(default_factory=_empty_list)
    summaries: list[dict[str, Any]] = field(default_factory=_empty_list)

    @property
    def scan_result_count(self) -> int:
        """Number of scan result rows acquired."""
        return len(self.scan_results)


def list_scan_result_dicts(
    client: Client,
    *,
    namespace: str,
    project_uuid: str,
    limit: int,
    status_filter: str | None = None,
) -> list[dict[str, Any]]:
    """List scan results for one project UUID as plain dicts."""
    rows = client.ScanResult.list_by_project(
        project_uuid,
        namespace=namespace,
        limit=limit,
        status_filter=status_filter,
    )
    return [object_to_dict(item) for item in rows]


def acquire_scan_results(
    client: Client,
    *,
    query_namespace: str,
    projects: Sequence[Any],
    limit: int = 25,
    status_filter: str | None = None,
    max_workers: int = 8,
) -> ScanResultsEvidence:
    """Fetch a bounded scan-result window for selected projects.

    Args:
        client: Injected Endor client (caller owns lifecycle).
        query_namespace: Fallback namespace when a project omits tenant_meta.
        projects: Project models or dicts (need ``uuid`` + optional namespace).
        limit: Per-project scan window (maps to ``list_by_project`` limit).
        status_filter: Optional client-side status match.
        max_workers: Parallelism when ``len(projects) > 1``.
    """
    project_dicts: list[dict[str, Any]] = [
        object_to_dict(p) if not isinstance(p, dict) else dict(p) for p in projects
    ]

    def _fetch(shard: ProjectShard) -> list[dict[str, Any]]:
        return list_scan_result_dicts(
            client,
            namespace=shard.namespace,
            project_uuid=shard.project_uuid,
            limit=limit,
            status_filter=status_filter,
        )

    all_results: list[dict[str, Any]]
    if len(project_dicts) > 1:
        all_results = parallel_collect_for_projects(
            project_dicts,
            _fetch,
            max_workers=max_workers,
            fallback_ns=query_namespace,
            progress_label="scan results projects",
        )
    else:
        all_results = []
        for project in project_dicts:
            project_uuid = dict_str(project, "uuid")
            project_ns = (
                nested_str(project, "tenant_meta", "namespace") or query_namespace
            )
            if not project_uuid:
                continue
            all_results.extend(
                list_scan_result_dicts(
                    client,
                    namespace=project_ns,
                    project_uuid=project_uuid,
                    limit=limit,
                    status_filter=status_filter,
                )
            )

    summaries = [scan_result_metrics(item) for item in all_results]
    skipped = sum(1 for p in project_dicts if not dict_str(p, "uuid"))
    warnings: list[str] = []
    if skipped:
        warnings.append(f"skipped_projects_without_uuid={skipped}")
    if limit > 0:
        warnings.append(f"per_project_limit={limit}; completeness unknown beyond limit")
    status = "partial" if warnings else "success"
    message = (
        "Scan results acquired with limits or skipped projects."
        if warnings
        else "Scan results acquired."
    )
    return ScanResultsEvidence(
        status=status,
        message=message,
        errors=[],
        query_namespace=query_namespace,
        project_count=len(project_dicts),
        scan_results=all_results,
        summaries=summaries,
    )
