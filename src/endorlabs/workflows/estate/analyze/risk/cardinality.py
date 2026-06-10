"""Risk-first version cardinality: rank packages by findings, drill down by version."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.estate.analyze.cardinality.columns import (
    RISK_RANKING_COLUMNS,
    RISK_VERSION_DETAIL_COLUMNS,
    RISK_WEIGHTED_CARDINALITY_SCHEMA,
)
from endorlabs.workflows.estate.analyze.cardinality.export import (
    _merge_usage_rows,
    _usage_row_from_group,
)
from endorlabs.workflows.estate.analyze.cardinality.group_list import (
    grouped_count_list_parameters_for_package_name,
    iter_group_buckets,
)
from endorlabs.workflows.estate.analyze.cardinality.tabular import TabularExport
from endorlabs.workflows.estate.analyze.cardinality.types import (
    RiskRankedCardinalityResult,
    RiskRankedCardinalityStats,
)
from endorlabs.workflows.estate.analyze.risk.scoring import (
    RiskScorer,
    aggregate_families,
    aggregate_family_findings_by_version,
    dm_package_name_for_key,
    join_version_usage_and_risk,
    rank_packages,
    resolve_scorer,
)
from endorlabs.workflows.estate.collect.findings import (
    DEFAULT_FINDING_CATEGORIES,
    collect_estate_findings,
    main_context_label,
)
from endorlabs.workflows.estate.collect.namespaces import list_estate_namespace_names

if TYPE_CHECKING:
    from endorlabs import Client

logger = get_resource_logger(__name__)

_DEFAULT_PAGE_SIZE = 500
_DEFAULT_TOP_N = 20


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _collect_usage_for_package(
    client: Client,
    estate_root: str,
    package_key: str,
    *,
    page_size: int,
    max_pages: int | None,
) -> list[dict[str, Any]]:
    dm_name = dm_package_name_for_key(package_key)
    namespace_names = list_estate_namespace_names(client, estate_root)
    raw_rows: list[dict[str, Any]] = []
    list_params = grouped_count_list_parameters_for_package_name(
        page_size=page_size,
        package_name=dm_name,
        main_context=True,
    )
    for namespace in namespace_names:
        for group_key, group_data in iter_group_buckets(
            client,
            namespace,
            list_params,
            max_pages=max_pages,
        ):
            row = _usage_row_from_group(
                estate_root,
                group_key,
                group_data,
                project_uuid="",
            )
            if row is None:
                continue
            if row["package_name"] != dm_name:
                continue
            raw_rows.append(row)
    return _merge_usage_rows(estate_root, raw_rows)


def _usage_rows_from_dependency_metadata(
    workspace_root: Path,
    estate_root: str,
    package_key: str,
) -> list[dict[str, Any]]:
    from endorlabs.workflows.estate.collect.dependency_metadata import (
        aggregate_usage_by_package_version,
        load_dependency_metadata_records,
    )

    dm_name = dm_package_name_for_key(package_key)
    totals = aggregate_usage_by_package_version(
        load_dependency_metadata_records(workspace_root),
        dm_name,
    )
    return [
        {
            "estate_root": estate_root,
            "package_name": dm_name,
            "package_version": version,
            "usage_count": count,
        }
        for version, count in sorted(totals.items())
    ]


def _version_cardinality(usage_rows: list[dict[str, Any]]) -> int:
    versions: set[str] = set()
    for row in usage_rows:
        version = str(row.get("package_version") or "")
        if version:
            versions.add(version)
    return len(versions)


def build_risk_document(
    *,
    estate_root: str,
    scorer_name: str,
    ranked: list[Any],
    packages: list[dict[str, Any]],
    warnings: list[str],
    top_n: int,
) -> dict[str, Any]:
    ranking_rows = [
        {
            "rank": index,
            "package_name": summary.package_name,
            "risk_score": summary.risk_score,
            "findings_critical": summary.findings_critical,
            "findings_high": summary.findings_high,
            "findings_total": summary.findings_total,
        }
        for index, summary in enumerate(ranked, start=1)
    ]
    return {
        "schema": RISK_WEIGHTED_CARDINALITY_SCHEMA,
        "estate_root": estate_root,
        "context_filter": main_context_label(),
        "finding_categories": list(DEFAULT_FINDING_CATEGORIES),
        "scorer": scorer_name,
        "top_n": top_n,
        "generated_at": _utc_now(),
        "ranking": ranking_rows,
        "packages": packages,
        "warnings": warnings,
    }


def export_risk_ranked_version_cardinality(
    client: Client,
    estate_root: str,
    *,
    top_n: int = _DEFAULT_TOP_N,
    scorer: RiskScorer | str | None = None,
    page_size: int | None = None,
    max_pages: int | None = None,
    max_workers: int = 16,
    findings_output: Path | None = None,
    risk_json_output: Path | None = None,
) -> RiskRankedCardinalityResult:
    """Rank estate packages by finding risk; drill into top-N version cardinality."""
    page_size = page_size or _DEFAULT_PAGE_SIZE
    if scorer is None:
        resolved_scorer = resolve_scorer("critical_high_count")
    elif isinstance(scorer, str):
        resolved_scorer = resolve_scorer(scorer)
    else:
        resolved_scorer = scorer

    finding_result = collect_estate_findings(
        client,
        estate_root,
        max_workers=max_workers,
        max_pages=max_pages,
        page_size=page_size,
        findings_output=findings_output,
    )
    if finding_result.errors and not finding_result.findings:
        return RiskRankedCardinalityResult(
            status="error",
            message="Finding collection failed for all projects",
            errors=finding_result.errors,
            stats=RiskRankedCardinalityStats(
                estate_root=estate_root,
                project_count=finding_result.project_count,
            ),
        )

    summaries = aggregate_families(finding_result.findings, resolved_scorer)
    ranked = rank_packages(summaries)
    top_packages = ranked[: max(top_n, 0)]

    namespace_names = list_estate_namespace_names(client, estate_root)
    package_payloads: list[dict[str, Any]] = []
    version_detail_rows: list[dict[str, Any]] = []
    warnings: list[str] = list(finding_result.errors)

    for summary in top_packages:
        dm_name = dm_package_name_for_key(summary.package_name)
        try:
            usage_rows = _collect_usage_for_package(
                client,
                estate_root,
                summary.package_name,
                page_size=page_size,
                max_pages=max_pages,
            )
        except Exception as exc:
            warnings.append(f"{summary.package_name}: dependency usage failed: {exc}")
            usage_rows = []

        version_risk = aggregate_family_findings_by_version(
            finding_result.findings,
            family_name=summary.package_name,
            scorer=resolved_scorer,
        )
        joined, join_warnings = join_version_usage_and_risk(
            usage_rows,
            version_risk,
            package_name=summary.package_name,
            usage_package_name=dm_name,
        )
        warnings.extend(join_warnings)
        max_version_risk = max(
            (item.risk_score for item in version_risk.values()),
            default=0.0,
        )

        versions_payload = [
            {
                "version": row["version"],
                "usage_count": row["usage_count"],
                "findings_critical": row["findings_critical"],
                "findings_high": row["findings_high"],
                "findings_total": row["findings_total"],
                "risk_score": row["risk_score"],
                "risk_intensity": round(
                    (row["risk_score"] / max_version_risk)
                    if max_version_risk > 0
                    else 0.0,
                    4,
                ),
                "orphan": row["orphan"],
            }
            for row in joined
        ]
        package_payloads.append(
            {
                "package_name": summary.package_name,
                "dm_package_name": dm_name,
                "risk_score": summary.risk_score,
                "findings_critical": summary.findings_critical,
                "findings_high": summary.findings_high,
                "findings_total": summary.findings_total,
                "version_cardinality": _version_cardinality(usage_rows),
                "versions": versions_payload,
            }
        )
        for row in joined:
            version_detail_rows.append(
                {
                    "estate_root": estate_root,
                    "package_name": summary.package_name,
                    "version": row["version"],
                    "usage_count": row["usage_count"],
                    "findings_critical": row["findings_critical"],
                    "findings_high": row["findings_high"],
                    "findings_total": row["findings_total"],
                    "risk_score": row["risk_score"],
                    "orphan": row["orphan"],
                }
            )

    ranking_table_rows = [
        {
            "estate_root": estate_root,
            "rank": index,
            "package_name": summary.package_name,
            "risk_score": summary.risk_score,
            "findings_critical": summary.findings_critical,
            "findings_high": summary.findings_high,
            "findings_total": summary.findings_total,
        }
        for index, summary in enumerate(ranked, start=1)
    ]

    document = build_risk_document(
        estate_root=estate_root,
        scorer_name=resolved_scorer.name,
        ranked=ranked,
        packages=package_payloads,
        warnings=warnings,
        top_n=top_n,
    )

    status = "success"
    if warnings:
        status = "partial" if package_payloads else "error"
    message = (
        f"Risk-ranked cardinality for top {len(top_packages)} of "
        f"{len(ranked)} packages from {len(finding_result.findings)} finding(s) "
        f"({finding_result.project_count} project(s), "
        f"{len(namespace_names)} namespace(s))."
    )

    return RiskRankedCardinalityResult(
        status=status,
        message=message,
        errors=warnings,
        stats=RiskRankedCardinalityStats(
            estate_root=estate_root,
            project_count=finding_result.project_count,
            finding_count=len(finding_result.findings),
            ranked_package_count=len(ranked),
            top_n=top_n,
            namespace_count=len(namespace_names),
        ),
        ranking_table=TabularExport(
            rows=ranking_table_rows,
            columns=list(RISK_RANKING_COLUMNS),
        ),
        version_detail_table=TabularExport(
            rows=version_detail_rows,
            columns=list(RISK_VERSION_DETAIL_COLUMNS),
        ),
        document=document,
    )


def analyze_risk_cardinality_from_workspace(
    workspace_root: Path,
    estate_root: str,
    *,
    top_n: int = _DEFAULT_TOP_N,
    scorer: RiskScorer | str | None = None,
) -> RiskRankedCardinalityResult:
    """Rank packages by findings and drill version cardinality from workspace JSONL."""
    from endorlabs.utils.artifact_io import write_json
    from endorlabs.workflows.estate.collect.finding_loader import load_finding_records
    from endorlabs.workflows.estate.collect.projects import load_project_records
    from endorlabs.workflows.estate.workspace.paths import ir_path

    if scorer is None:
        resolved_scorer = resolve_scorer("critical_high_count")
    elif isinstance(scorer, str):
        resolved_scorer = resolve_scorer(scorer)
    else:
        resolved_scorer = scorer

    findings = load_finding_records(workspace_root)
    project_count = len(load_project_records(workspace_root))
    if not findings:
        return RiskRankedCardinalityResult(
            status="error",
            message="No findings in workspace data/finding.jsonl",
            errors=["empty finding resource"],
            stats=RiskRankedCardinalityStats(estate_root=estate_root),
        )

    summaries = aggregate_families(findings, resolved_scorer)
    ranked = rank_packages(summaries)
    top_packages = ranked[: max(top_n, 0)]
    warnings: list[str] = []
    package_payloads: list[dict[str, Any]] = []
    version_detail_rows: list[dict[str, Any]] = []

    for summary in top_packages:
        dm_name = dm_package_name_for_key(summary.package_name)
        usage_rows = _usage_rows_from_dependency_metadata(
            workspace_root, estate_root, summary.package_name
        )
        version_risk = aggregate_family_findings_by_version(
            findings,
            family_name=summary.package_name,
            scorer=resolved_scorer,
        )
        joined, join_warnings = join_version_usage_and_risk(
            usage_rows,
            version_risk,
            package_name=summary.package_name,
            usage_package_name=dm_name,
        )
        warnings.extend(join_warnings)
        max_version_risk = max(
            (item.risk_score for item in version_risk.values()),
            default=0.0,
        )
        versions_payload = [
            {
                "version": row["version"],
                "usage_count": row["usage_count"],
                "findings_critical": row["findings_critical"],
                "findings_high": row["findings_high"],
                "findings_total": row["findings_total"],
                "risk_score": row["risk_score"],
                "risk_intensity": round(
                    (row["risk_score"] / max_version_risk)
                    if max_version_risk > 0
                    else 0.0,
                    4,
                ),
                "orphan": row["orphan"],
            }
            for row in joined
        ]
        package_payloads.append(
            {
                "package_name": summary.package_name,
                "dm_package_name": dm_name,
                "risk_score": summary.risk_score,
                "findings_critical": summary.findings_critical,
                "findings_high": summary.findings_high,
                "findings_total": summary.findings_total,
                "version_cardinality": _version_cardinality(usage_rows),
                "versions": versions_payload,
            }
        )
        for row in joined:
            version_detail_rows.append(
                {
                    "estate_root": estate_root,
                    "package_name": summary.package_name,
                    "version": row["version"],
                    "usage_count": row["usage_count"],
                    "findings_critical": row["findings_critical"],
                    "findings_high": row["findings_high"],
                    "findings_total": row["findings_total"],
                    "risk_score": row["risk_score"],
                    "orphan": row["orphan"],
                }
            )

    ranking_table_rows = [
        {
            "estate_root": estate_root,
            "rank": index,
            "package_name": summary.package_name,
            "risk_score": summary.risk_score,
            "findings_critical": summary.findings_critical,
            "findings_high": summary.findings_high,
            "findings_total": summary.findings_total,
        }
        for index, summary in enumerate(ranked, start=1)
    ]

    document = build_risk_document(
        estate_root=estate_root,
        scorer_name=resolved_scorer.name,
        ranked=ranked,
        packages=package_payloads,
        warnings=warnings,
        top_n=top_n,
    )
    write_json(
        str(ir_path(workspace_root, "risk_cardinality.json")),
        document,
        base_dir=workspace_root,
    )

    status = "success"
    if warnings:
        status = "partial" if package_payloads else "error"
    message = (
        f"Risk-ranked cardinality for top {len(top_packages)} of "
        f"{len(ranked)} packages from {len(findings)} finding(s) "
        f"({project_count} project(s))."
    )
    return RiskRankedCardinalityResult(
        status=status,
        message=message,
        errors=warnings,
        stats=RiskRankedCardinalityStats(
            estate_root=estate_root,
            project_count=project_count,
            finding_count=len(findings),
            ranked_package_count=len(ranked),
            top_n=top_n,
        ),
        ranking_table=TabularExport(
            rows=ranking_table_rows,
            columns=list(RISK_RANKING_COLUMNS),
        ),
        version_detail_table=TabularExport(
            rows=version_detail_rows,
            columns=list(RISK_VERSION_DETAIL_COLUMNS),
        ),
        document=document,
    )
