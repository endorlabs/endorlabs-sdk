"""Orchestrate inventory → resolve → join for one or more namespaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from endorlabs.context.paths import namespace_path_slug, task_activity_dir
from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.license_export.inventory import (
    collect_dependency_inventory,
    load_inventory_jsonl,
    unique_package_version_uuids,
)
from endorlabs.workflows.license_export.join import (
    ExportFormat,
    default_join_filename,
    write_joined_export,
)
from endorlabs.workflows.license_export.resolve import (
    LICENSE_CACHE_FILENAME,
    LICENSE_OBJECTS_FILENAME,
    load_license_cache,
    resolve_licenses,
)
from endorlabs.workflows.license_export.summary import (
    ElapsedTimer,
    build_export_summary,
    format_summary_line,
    summarize_license_cache,
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
    inventory_rows: int = 0
    join_path: str = ""
    join_rows: int = 0
    project_count: int = 0
    complete_shards: int = 0
    failed_shards: int = 0


@dataclass
class LicenseExportRunResult(WorkflowResult):
    """Multi-namespace ``run`` outcome."""

    format: str = ""
    output_dir: str = ""
    summary_path: str = ""
    summary: dict[str, Any] = field(default_factory=dict[str, Any])
    namespace_results: list[NamespaceExportResult] = field(
        default_factory=_empty_ns_results
    )


def default_output_dir(namespace: str) -> Path:
    """``.endorlabs/tasks/<slug>-<date>/licenses/`` for the primary namespace."""
    path = task_activity_dir(namespace, "licenses")
    path.mkdir(parents=True, exist_ok=True)
    return path


def namespace_work_dir(base: Path, namespace: str) -> Path:
    """Per-namespace subdirectory under the export base output dir."""
    path = base / namespace_path_slug(namespace)
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_license_export(
    client: Client,
    *,
    namespaces: list[str],
    output_dir: str | Path | None = None,
    export_format: ExportFormat = "csv",
    max_workers: int | None = None,
    max_pages: int | None = None,
    page_size: int = 500,
    resume: bool = False,
    overwrite: bool = False,
    license_cache: str | Path | None = None,
    batch_size: int = 100,
    extra_filter: str | None = None,
    mask: str | None = None,
    include_license_object: bool = False,
) -> LicenseExportRunResult:
    """Full pipeline for each namespace; shared license cache across namespaces."""
    timer = ElapsedTimer()
    if not namespaces:
        return LicenseExportRunResult(
            status="error",
            message="At least one namespace is required",
            errors=["At least one namespace is required"],
            format=export_format,
        )

    primary = namespaces[0]
    base = Path(output_dir) if output_dir is not None else default_output_dir(primary)
    base.mkdir(parents=True, exist_ok=True)
    cache_path = (
        Path(license_cache)
        if license_cache is not None
        else base / LICENSE_CACHE_FILENAME
    )
    objects_path = base / LICENSE_OBJECTS_FILENAME

    ns_results: list[NamespaceExportResult] = []
    errors: list[str] = []

    for namespace in namespaces:
        ns = namespace.strip()
        if not ns:
            continue
        work = namespace_work_dir(base, ns)

        inv = collect_dependency_inventory(
            client,
            namespace=ns,
            output_dir=work,
            max_workers=max_workers,
            max_pages=max_pages,
            page_size=page_size,
            resume=resume,
            overwrite=overwrite,
            extra_filter=extra_filter,
            mask=mask,
        )
        if inv.errors:
            errors.extend(inv.errors)
        if inv.status == "error":
            ns_results.append(
                NamespaceExportResult(
                    status="error",
                    message=inv.message,
                    errors=list(inv.errors),
                    namespace=ns,
                    inventory_rows=inv.row_count,
                    project_count=inv.project_count,
                    complete_shards=inv.complete_shards,
                    failed_shards=inv.failed_shards,
                )
            )
            continue

        rows = load_inventory_jsonl(Path(inv.inventory_path))
        pv_uuids = unique_package_version_uuids(rows)
        resolved = resolve_licenses(
            client,
            namespace=ns,
            package_version_uuids=pv_uuids,
            cache_path=cache_path,
            batch_size=batch_size,
            max_workers=max_workers,
            overwrite=False,  # shared cache — never wipe mid multi-NS run
            include_license_object=include_license_object,
            objects_path=objects_path,
        )
        if resolved.errors:
            errors.extend(resolved.errors)

        join_path = work / default_join_filename(ns, export_format)
        joined = write_joined_export(
            inventory_path=inv.inventory_path,
            cache_path=cache_path,
            output_path=join_path,
            export_format=export_format,
            objects_path=objects_path if include_license_object else None,
            include_license_object=include_license_object,
        )

        status = "success"
        if inv.status == "partial" or resolved.status in {"partial", "error"}:
            status = "partial" if joined.row_count else "error"

        ns_results.append(
            NamespaceExportResult(
                status=status,
                message=f"{inv.message}; {resolved.message}; {joined.message}",
                errors=list(inv.errors) + list(resolved.errors),
                namespace=ns,
                inventory_rows=inv.row_count,
                join_path=str(join_path),
                join_rows=joined.row_count,
                project_count=inv.project_count,
                complete_shards=inv.complete_shards,
                failed_shards=inv.failed_shards,
            )
        )

    ok = [r for r in ns_results if r.status == "success"]
    partial = [r for r in ns_results if r.status == "partial"]
    if not ns_results or (errors and not ok and not partial):
        status = "error"
    elif errors or partial:
        status = "partial"
    else:
        status = "success"

    license_stats = summarize_license_cache(cache_path)
    all_inv_rows = sum(r.inventory_rows for r in ns_results)
    all_join = sum(r.join_rows for r in ns_results)
    unique_pvs = len(load_license_cache(cache_path))

    message = (
        f"License export: {len(ok)} ok, {len(partial)} partial, "
        f"{len(ns_results) - len(ok) - len(partial)} failed "
        f"of {len(ns_results)} namespace(s) → {base}"
    )
    summary = build_export_summary(
        namespaces=[r.namespace for r in ns_results],
        output_dir=base,
        export_format=export_format,
        workers=max_workers,
        elapsed_seconds=timer.elapsed(),
        projects_total=sum(r.project_count for r in ns_results),
        projects_complete=sum(r.complete_shards for r in ns_results),
        projects_failed=sum(r.failed_shards for r in ns_results),
        inventory_rows=all_inv_rows,
        unique_pvs=unique_pvs,
        join_rows=all_join,
        license_consensus=license_stats["consensus"],
        license_query=license_stats["query"],
        license_missing=license_stats["missing"],
        license_with_primary_spdx=license_stats["with_primary_spdx"],
        join_paths=[r.join_path for r in ns_results if r.join_path],
        license_cache_path=str(cache_path),
        license_objects_path=str(objects_path) if include_license_object else "",
        status=status,
        message=message,
        errors=errors,
    )
    summary_path = write_export_summary(base, summary)

    return LicenseExportRunResult(
        status=status,
        message=message,
        errors=errors,
        format=export_format,
        output_dir=str(base),
        summary_path=str(summary_path),
        summary=summary,
        namespace_results=ns_results,
    )


def run_inventory_only(
    client: Client,
    *,
    namespace: str,
    output_dir: str | Path,
    **kwargs: Any,
) -> Any:
    """Thin wrapper for CLI ``inventory`` subcommand."""
    return collect_dependency_inventory(
        client, namespace=namespace, output_dir=output_dir, **kwargs
    )


__all__ = [
    "LicenseExportRunResult",
    "NamespaceExportResult",
    "default_output_dir",
    "format_summary_line",
    "namespace_work_dir",
    "run_inventory_only",
    "run_license_export",
]
