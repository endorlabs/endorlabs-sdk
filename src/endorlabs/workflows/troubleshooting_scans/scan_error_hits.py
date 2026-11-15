"""Embedded ``spec.logs`` error-pattern search for host injection (SDK-006)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from endorlabs.tools.list_sharding import ProjectShard
from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.troubleshooting_scans.common import (
    object_to_dict,
    parallel_collect_for_projects,
)
from endorlabs.workflows.wire_access import dict_str, nested_dict, nested_str

if TYPE_CHECKING:
    from endorlabs.client_surface import Client


def _empty_hits() -> list[dict[str, Any]]:
    return []


@dataclass
class ScanErrorHitsEvidence(WorkflowResult):
    """Typed embedded-log pattern hits; no artifact paths."""

    query_namespace: str = ""
    error_pattern: str = ""
    project_count: int = 0
    hits: list[dict[str, Any]] = field(default_factory=_empty_hits)

    @property
    def hit_count(self) -> int:
        """Number of matching log lines across selected projects."""
        return len(self.hits)


def search_embedded_scan_errors(
    client: Client,
    *,
    projects: Sequence[Any],
    error_pattern: str,
    query_namespace: str,
    limit: int = 25,
    max_workers: int = 8,
) -> ScanErrorHitsEvidence:
    """Search embedded ``spec.logs`` lines for *error_pattern* (case-insensitive).

    Uses ``ScanResult.list_by_project`` per project; does not call ScanLog API.
    """
    pattern = re.compile(error_pattern, re.IGNORECASE)
    project_dicts: list[dict[str, Any]] = [
        object_to_dict(p) if not isinstance(p, dict) else dict(p) for p in projects
    ]

    def _search_project(shard: ProjectShard) -> list[dict[str, Any]]:
        project_hits: list[dict[str, Any]] = []
        scan_results = [
            object_to_dict(item)
            for item in client.ScanResult.list_by_project(
                shard.project_uuid,
                namespace=shard.namespace,
                limit=limit,
            )
        ]
        for scan_result in scan_results:
            scan_uuid = dict_str(scan_result, "uuid")
            spec = nested_dict(scan_result, "spec")
            scan_logs_raw = spec.get("logs")
            scan_logs: list[Any] = (
                cast("list[Any]", scan_logs_raw)
                if isinstance(scan_logs_raw, list)
                else []
            )
            project_hits.extend(
                {
                    "project_uuid": shard.project_uuid,
                    "project_namespace": shard.namespace,
                    "scan_result_uuid": scan_uuid,
                    "status": spec.get("status"),
                    "match_line": str(line),
                }
                for line in scan_logs
                if pattern.search(str(line))
            )
        return project_hits

    if len(project_dicts) > 1:
        hits = parallel_collect_for_projects(
            project_dicts,
            _search_project,
            max_workers=max_workers,
            fallback_ns=query_namespace,
            progress_label="scan error search projects",
        )
    else:
        hits = []
        for project in project_dicts:
            project_uuid = dict_str(project, "uuid")
            project_ns = (
                nested_str(project, "tenant_meta", "namespace") or query_namespace
            )
            if not project_uuid:
                continue
            shard = ProjectShard(
                project_uuid=str(project_uuid), namespace=str(project_ns)
            )
            hits.extend(_search_project(shard))

    return ScanErrorHitsEvidence(
        query_namespace=query_namespace,
        error_pattern=error_pattern,
        project_count=len(project_dicts),
        hits=hits,
    )
