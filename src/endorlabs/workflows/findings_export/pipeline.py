"""Orchestrate MAIN-context Finding export for one or more namespaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from endorlabs.context.paths import namespace_path_slug, task_activity_dir
from endorlabs.tools.list_bounds import resolve_collect_max_workers
from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.findings_export.collect import collect_findings_export
from endorlabs.workflows.findings_export.summary import (
    ElapsedTimer,
    build_export_summary,
    write_export_summary,
)

if TYPE_CHECKING:
    from endorlabs.client_surface import Client


def _empty_ns_results() -> list[NamespaceExportResult]:
    return []


@dataclass
class NamespaceExportResult(WorkflowResult):
    """Per-namespace outcome inside a multi-NS ``run``."""

    namespace: str = ""
    findings_path: str = ""
    projects_path: str = ""
    finding_rows: int = 0
    project_count: int = 0
    complete_shards: int = 0
    failed_shards: int = 0


@dataclass
class FindingsExportRunResult(WorkflowResult):
    """Multi-namespace findings export outcome."""

    output_dir: str = ""
    summary_path: str = ""
    summary: dict[str, Any] = field(default_factory=dict[str, Any])
    namespace_results: list[NamespaceExportResult] = field(
        default_factory=_empty_ns_results
    )


def default_output_dir(namespace: str) -> Path:
    """``.endorlabs/tasks/<slug>-<date>/findings/`` for the primary namespace."""
    path = task_activity_dir(namespace, "findings")
    path.mkdir(parents=True, exist_ok=True)
    return path


def namespace_work_dir(base: Path, namespace: str) -> Path:
    """Per-namespace subdirectory under the export base output dir."""
    path = base / namespace_path_slug(namespace)
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_findings_export(
    client: Client,
    *,
    namespaces: list[str],
    output_dir: str | Path | None = None,
    max_workers: int | None = None,
    max_pages: int | None = None,
    page_size: int = 500,
    resume: bool = False,
    overwrite: bool = False,
    extra_filter: str | None = None,
    mask: str | None = None,
) -> FindingsExportRunResult:
    """Collect MAIN Finding JSONL for each namespace under *output_dir*."""
    timer = ElapsedTimer()
    if not namespaces:
        return FindingsExportRunResult(
            status="error",
            message="At least one namespace is required",
            errors=["At least one namespace is required"],
        )

    primary = namespaces[0]
    base = Path(output_dir) if output_dir is not None else default_output_dir(primary)
    base.mkdir(parents=True, exist_ok=True)
    workers = resolve_collect_max_workers(max_workers)

    ns_results: list[NamespaceExportResult] = []
    all_errors: list[str] = []
    projects_total = 0
    projects_complete = 0
    projects_failed = 0
    finding_rows = 0
    ns_paths: list[dict[str, str]] = []

    for ns in namespaces:
        work = namespace_work_dir(base, ns)
        collected = collect_findings_export(
            client,
            namespace=ns,
            output_dir=work,
            max_workers=workers,
            max_pages=max_pages,
            page_size=page_size,
            resume=resume,
            overwrite=overwrite,
            extra_filter=extra_filter,
            mask=mask,
        )
        ns_results.append(
            NamespaceExportResult(
                status=collected.status,
                message=collected.message,
                errors=list(collected.errors),
                namespace=ns,
                findings_path=collected.findings_path,
                projects_path=collected.projects_path,
                finding_rows=collected.row_count,
                project_count=collected.project_count,
                complete_shards=collected.complete_shards,
                failed_shards=collected.failed_shards,
            )
        )
        all_errors.extend(collected.errors)
        projects_total += collected.project_count
        projects_complete += collected.complete_shards
        projects_failed += collected.failed_shards
        finding_rows += collected.row_count
        ns_paths.append(
            {
                "namespace": ns,
                "findings": collected.findings_path,
                "projects": collected.projects_path,
                "output_dir": collected.output_dir,
            }
        )

    if any(r.status == "error" for r in ns_results) and finding_rows == 0:
        status = "error"
    elif all_errors or any(r.status == "partial" for r in ns_results):
        status = "partial"
    else:
        status = "success"

    message = (
        f"Findings export: {finding_rows} finding row(s) across "
        f"{len(namespaces)} namespace(s); "
        f"{projects_complete}/{projects_total} project shard(s) complete"
    )
    summary = build_export_summary(
        namespaces=namespaces,
        output_dir=base,
        workers=workers,
        elapsed_seconds=timer.elapsed(),
        projects_total=projects_total,
        projects_complete=projects_complete,
        projects_failed=projects_failed,
        finding_rows=finding_rows,
        mask=mask,
        status=status,
        message=message,
        errors=all_errors,
        namespace_paths=ns_paths,
    )
    summary_path = write_export_summary(base, summary)

    return FindingsExportRunResult(
        status=status,
        message=message,
        errors=all_errors,
        output_dir=str(base),
        summary_path=str(summary_path),
        summary=summary,
        namespace_results=ns_results,
    )
