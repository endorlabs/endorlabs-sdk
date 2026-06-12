"""Estate-wide main-context SCA/vulnerability finding collection."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import endorlabs
from endorlabs.tools.list_sharding import (
    ParentShard,
    parallel_map_shards,
    project_model_to_shard,
)
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.estate.analyze.risk.scoring import normalize_finding_record
from endorlabs.workflows.estate.collect.namespaces import list_estate_namespace_names
from endorlabs.workflows.estate.filters.main_context import (
    MAIN_CONTEXT_LIST_FILTER,
    MAIN_CONTEXT_TYPE,
)

if TYPE_CHECKING:
    from endorlabs import Client

logger = get_resource_logger(__name__)

FINDING_CATEGORY_SCA = "FINDING_CATEGORY_SCA"
FINDING_CATEGORY_VULNERABILITY = "FINDING_CATEGORY_VULNERABILITY"

DEFAULT_FINDING_CATEGORIES: tuple[str, ...] = (
    FINDING_CATEGORY_SCA,
    FINDING_CATEGORY_VULNERABILITY,
)

FINDING_LIST_MASK = (
    "uuid,"
    "spec.level,"
    "spec.finding_categories,"
    "spec.target_dependency_package_name,"
    "spec.target_dependency_name,"
    "spec.target_dependency_version,"
    "spec.finding_tags"
)


def findings_filter_for_project(project_uuid: str) -> str:
    """Main-context project-scoped SCA + vulnerability finding filter."""
    category = endorlabs.F("spec.finding_categories").contains(
        FINDING_CATEGORY_SCA
    ) | endorlabs.F("spec.finding_categories").contains(FINDING_CATEGORY_VULNERABILITY)
    return str(
        (endorlabs.F("context.type") == MAIN_CONTEXT_TYPE)
        & (endorlabs.F("spec.project_uuid") == project_uuid)
        & category
    )


def discover_project_shards(client: Client, estate_root: str) -> list[ParentShard]:
    """List project shards across estate counting namespaces."""
    shards: list[ParentShard] = []
    seen: set[str] = set()
    for namespace in list_estate_namespace_names(client, estate_root):
        projects = client.Project.list(namespace=namespace, traverse=False)
        for project in projects:
            project_uuid = getattr(project, "uuid", None)
            if not isinstance(project_uuid, str) or not project_uuid:
                continue
            if project_uuid in seen:
                continue
            seen.add(project_uuid)
            shards.append(project_model_to_shard(project, namespace))
    return shards


def _fetch_findings_for_shard(
    client: Client,
    shard: ParentShard,
    *,
    max_pages: int | None,
    page_size: int,
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        rows = client.Finding.list(
            filter=findings_filter_for_project(shard.key),
            namespace=shard.namespace,
            mask=FINDING_LIST_MASK,
            max_pages=max_pages,
            page_size=page_size,
        )
    except Exception as exc:
        return [], f"{shard.namespace}/{shard.key}: {exc}"
    normalized = [normalize_finding_record(row) for row in rows]
    return normalized, None


@dataclass
class FindingCollectResult:
    """Outcome of estate finding collection."""

    findings: list[dict[str, Any]] = field(default_factory=list)
    project_count: int = 0
    errors: list[str] = field(default_factory=list)


def collect_estate_findings(
    client: Client,
    estate_root: str,
    *,
    max_workers: int = 16,
    max_pages: int | None = None,
    page_size: int = 100,
    findings_output: Path | None = None,
) -> FindingCollectResult:
    """Collect main-context SCA/vulnerability findings for all estate projects."""
    shards = discover_project_shards(client, estate_root)
    result = FindingCollectResult(project_count=len(shards))
    if not shards:
        return result

    handle = None
    if findings_output is not None:
        findings_output.parent.mkdir(parents=True, exist_ok=True)
        handle = findings_output.open("w", encoding="utf-8")

    def _worker(shard: ParentShard) -> tuple[list[dict[str, Any]], str | None]:
        return _fetch_findings_for_shard(
            client,
            shard,
            max_pages=max_pages,
            page_size=page_size,
        )

    try:
        for batch, err in parallel_map_shards(
            shards,
            _worker,
            max_workers=max_workers,
            progress_label="finding projects",
        ):
            if err:
                result.errors.append(err)
                logger.warning("Finding collect failed: %s", err)
                continue
            result.findings.extend(batch)
            if handle is not None:
                for row in batch:
                    handle.write(json.dumps(row, ensure_ascii=True))
                    handle.write("\n")
    finally:
        if handle is not None:
            handle.close()

    logger.info(
        "Collected %s finding records from %s project(s)",
        len(result.findings),
        result.project_count,
    )
    return result


def main_context_label() -> str:
    return MAIN_CONTEXT_LIST_FILTER
