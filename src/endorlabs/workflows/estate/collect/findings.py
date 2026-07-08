"""Estate-wide main-context SCA/vulnerability finding collection."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.estate.analyze.risk.scoring import normalize_finding_record
from endorlabs.workflows.query_collect import collect_project_findings_via_query

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


def main_context_label() -> str:
    """Human-readable main-context filter label for artifacts."""
    from endorlabs.filters import MAIN_CONTEXT_LIST_FILTER

    return MAIN_CONTEXT_LIST_FILTER


def findings_filter_for_project(_project_uuid: str) -> str:
    """Main-context SCA + vulnerability finding filter (no project_uuid clause)."""
    from endorlabs.filters import estate_findings_filter

    return estate_findings_filter()


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
    max_pages: int | None = None,
    findings_output: Path | None = None,
) -> FindingCollectResult:
    """Collect main-context SCA/vulnerability findings for all estate projects."""
    topology = client.Query.Project.discover(estate_root, traverse=True)
    projects = topology.projects
    result = FindingCollectResult(project_count=len(projects))
    if not projects:
        return result

    try:
        rows = collect_project_findings_via_query(
            client,
            projects,
            mask=FINDING_LIST_MASK,
            max_root_pages=max_pages,
        )
        result.findings = [normalize_finding_record(row) for row in rows]
    except Exception as exc:
        result.errors.append(str(exc))
        logger.warning("Finding collect via Query failed: %s", exc)
        return result

    if findings_output is not None:
        findings_output.parent.mkdir(parents=True, exist_ok=True)
        with findings_output.open("w", encoding="utf-8") as handle:
            for row in result.findings:
                handle.write(json.dumps(row, ensure_ascii=True))
                handle.write("\n")

    logger.info(
        "Collected %s finding records from %s project(s)",
        len(result.findings),
        result.project_count,
    )
    return result
