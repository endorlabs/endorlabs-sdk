"""Export version cardinality for DependencyMetadata across an estate.

Version cardinality is the number of distinct package versions in use for each
package name (server-side aggregate by package name + package version, then
rolled up per name).

Example::

    import endorlabs
    from endorlabs.workflows.estate.analyze.cardinality.tabular import write_table
    from endorlabs.workflows.estate import export_version_cardinality

    client = endorlabs.Client(tenant="tenant.example")
    result = export_version_cardinality(
        client, "tenant.example", output_path="version_cardinality.csv"
    )
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Any

import endorlabs
from endorlabs.context.paths import default_runs_dir
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.estate.analyze.cardinality.tabular import (
    TabularExport,
    write_table,
)
from endorlabs.workflows.estate.collect.namespaces import (
    discover_estate_namespace_names,
    namespaces_for_grouped_counts,
)

from .columns import (
    PACKAGE_NAME_PATH,
    PACKAGE_VERSION_PATH,
    VERSION_CARDINALITY_COLUMNS,
    VERSION_USAGE_COLUMNS,
)
from .group_list import (
    grouped_count_list_parameters,
    grouped_count_list_parameters_for_importer_package_version,
)
from .remediation import RemediationComparisonResult, analyze_intra_minor_remediation
from .types import VersionCardinalityResult, VersionCardinalityStats

if TYPE_CHECKING:
    from endorlabs import Client
    from endorlabs.core.types import ListParameters
    from endorlabs.operations.list_response import GroupBucket

logger = get_resource_logger(__name__)

_DEFAULT_PAGE_SIZE = 500
_DEFAULT_PROGRESS_BATCH = 100
_DEFAULT_MAX_PROJECT_WORKERS = 16
# Per-namespace grouped lists on large estates can exceed the Client default (60s).
_DEFAULT_GROUPED_REQUEST_TIMEOUT = 900.0


def _resolve_request_timeout(cli_value: float | None) -> float:
    from endorlabs.utils.request_timeout import resolve_request_timeout

    return resolve_request_timeout(cli_value, default=_DEFAULT_GROUPED_REQUEST_TIMEOUT)


def _configure_cli_logging() -> None:
    logger.setLevel(logging.INFO)
    if any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(handler)


def _emit_progress(processed: int, total: int | None, *, label: str) -> None:
    suffix = f"{processed}/{total}" if total is not None else f"{processed}/?"
    line = f"{label}: {suffix}\n"
    sys.stderr.write(line)
    sys.stderr.flush()
    logger.info("%s %s", label, suffix)


def _usage_row_from_group(
    estate_root: str,
    bucket: GroupBucket,
    *,
    project_uuid: str,
) -> dict[str, Any] | None:
    fields = bucket.parsed
    package_name = fields.get(PACKAGE_NAME_PATH, "")
    package_version = fields.get(PACKAGE_VERSION_PATH, "")
    if not package_name:
        return None
    return {
        "estate_root": estate_root,
        "project_uuid": project_uuid,
        "package_name": package_name,
        "package_version": package_version,
        "usage_count": bucket.count,
    }


def _merge_usage_rows(
    estate_root: str,
    usage_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sum ``usage_count`` for the same package name and version across namespaces."""
    totals: dict[tuple[str, str], int] = defaultdict(int)
    for row in usage_rows:
        name = str(row["package_name"])
        version = str(row.get("package_version") or "")
        totals[(name, version)] += int(row.get("usage_count") or 0)
    merged: list[dict[str, Any]] = []
    for (package_name, package_version), usage_count in sorted(totals.items()):
        merged.append(
            {
                "estate_root": estate_root,
                "package_name": package_name,
                "package_version": package_version,
                "usage_count": usage_count,
            }
        )
    return merged


def _merge_usage_rows_by_project(
    estate_root: str,
    usage_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sum usage_count by project, package name, and version (pivot-friendly)."""
    totals: dict[tuple[str, str, str], int] = defaultdict(int)
    for row in usage_rows:
        project_uuid = str(row.get("project_uuid") or "")
        name = str(row["package_name"])
        version = str(row.get("package_version") or "")
        totals[(project_uuid, name, version)] += int(row.get("usage_count") or 0)
    merged: list[dict[str, Any]] = []
    for (project_uuid, package_name, package_version), usage_count in sorted(
        totals.items()
    ):
        merged.append(
            {
                "estate_root": estate_root,
                "project_uuid": project_uuid,
                "package_name": package_name,
                "package_version": package_version,
                "usage_count": usage_count,
            }
        )
    return merged


def _rollup_version_cardinality(
    estate_root: str,
    usage_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    versions_by_name: dict[str, set[str]] = defaultdict(set)
    usage_by_name: dict[str, int] = defaultdict(int)

    for row in usage_rows:
        name = str(row["package_name"])
        version = str(row.get("package_version") or "")
        if version:
            versions_by_name[name].add(version)
        usage_by_name[name] += int(row.get("usage_count") or 0)

    return [
        {
            "estate_root": estate_root,
            "package_name": package_name,
            "version_cardinality": len(versions_by_name[package_name]),
            "dependency_usage_rows": usage_by_name[package_name],
        }
        for package_name in sorted(versions_by_name)
    ]


def _project_wire_namespace(project: Any, fallback_namespace: str) -> str:
    tenant_meta = getattr(project, "tenant_meta", None)
    parent_ns = (
        getattr(tenant_meta, "namespace", None) if tenant_meta is not None else None
    )
    if parent_ns:
        return str(parent_ns)
    return fallback_namespace


def _dedupe_projects_by_uuid(projects: list[Any]) -> list[Any]:
    seen: set[str] = set()
    unique: list[Any] = []
    for project in projects:
        project_uuid = getattr(project, "uuid", None)
        if not isinstance(project_uuid, str) or not project_uuid:
            continue
        if project_uuid in seen:
            continue
        seen.add(project_uuid)
        unique.append(project)
    return unique


def _list_projects_in_namespace(client: Client, namespace: str) -> list[Any]:
    projects = client.Project.list(namespace=namespace, traverse=False)
    return _dedupe_projects_by_uuid(list(projects))


def _list_package_versions_for_project(
    client: Client,
    namespace: str,
    project: Any,
) -> list[Any]:
    package_versions = client.PackageVersion.list_by_project(
        project,
        namespace=namespace,
        traverse=False,
    )
    seen: set[str] = set()
    unique: list[Any] = []
    for pv in package_versions:
        pv_uuid = getattr(pv, "uuid", None)
        if not isinstance(pv_uuid, str) or not pv_uuid or pv_uuid in seen:
            continue
        seen.add(pv_uuid)
        unique.append(pv)
    return unique


def _collect_importer_shards(
    client: Client,
    namespace: str,
) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Return importer PV shards as ``(namespace, project_uuid, pv_uuid)`` tuples."""
    errors: list[str] = []
    try:
        projects = _list_projects_in_namespace(client, namespace)
    except Exception as exc:
        return [], [f"{namespace}: project list failed: {exc}"]

    shards: list[tuple[str, str, str]] = []
    for project in projects:
        project_uuid = str(project.uuid)
        wire_ns = _project_wire_namespace(project, namespace)
        try:
            package_versions = _list_package_versions_for_project(
                client, wire_ns, project
            )
        except Exception as exc:
            errors.append(
                f"{namespace}/{project_uuid}: package version list failed: {exc}"
            )
            continue
        for pv in package_versions:
            importer_pv_uuid = str(pv.uuid)
            shards.append((wire_ns, project_uuid, importer_pv_uuid))
    return shards, errors


def _iter_group_buckets(
    client: Client,
    namespace: str,
    list_params: ListParameters,
    *,
    max_pages: int | None,
) -> Iterator[GroupBucket]:
    paths = list_params.group_aggregation_paths
    if not paths:
        raise ValueError("list_params.group_aggregation_paths is required")
    return client.DependencyMetadata.list_groups(
        namespace=namespace,
        list_params=list_params,
        paths=list(paths),
        max_pages=max_pages,
    )


def _fetch_grouped_usage_rows(
    client: Client,
    namespace: str,
    list_params: ListParameters,
    estate_root: str,
    *,
    project_uuid: str,
    max_pages: int | None,
    progress_batch: int,
) -> tuple[list[dict[str, Any]], int]:
    usage_rows: list[dict[str, Any]] = []
    processed_groups = 0
    for bucket in _iter_group_buckets(
        client,
        namespace,
        list_params,
        max_pages=max_pages,
    ):
        row = _usage_row_from_group(
            estate_root,
            bucket,
            project_uuid=project_uuid,
        )
        if row is not None:
            usage_rows.append(row)
        processed_groups += 1
        if progress_batch > 0 and processed_groups % progress_batch == 0:
            _emit_progress(processed_groups, None, label="groups")
    return usage_rows, processed_groups


def _fetch_importer_package_version_grouped_usage_rows(
    client: Client,
    namespace: str,
    project_uuid: str,
    importer_package_version_uuid: str,
    *,
    page_size: int,
    estate_root: str,
    max_pages: int | None,
) -> tuple[list[dict[str, Any]], int]:
    list_params = grouped_count_list_parameters_for_importer_package_version(
        page_size=page_size,
        package_version_uuid=importer_package_version_uuid,
    )
    return _fetch_grouped_usage_rows(
        client,
        namespace,
        list_params,
        estate_root,
        project_uuid=project_uuid,
        max_pages=max_pages,
        progress_batch=0,
    )


def _fetch_namespace_via_importer_package_versions(
    client: Client,
    namespace: str,
    estate_root: str,
    *,
    page_size: int,
    max_pages: int | None,
    progress_batch: int,
    max_project_workers: int,
) -> tuple[list[dict[str, Any]], int, int, int, list[str]]:
    """Grouped DependencyMetadata per importer PackageVersion (parallel shards)."""
    shards, list_errors = _collect_importer_shards(client, namespace)
    errors: list[str] = list(list_errors)
    if not shards and list_errors:
        return [], 0, 0, 0, errors
    if not shards:
        return [], 0, 0, 0, errors

    usage_rows: list[dict[str, Any]] = []
    total_groups = 0
    project_ids = {project_uuid for _, project_uuid, _ in shards}
    workers = max(1, min(max_project_workers, len(shards)))

    def _query_shard(
        shard: tuple[str, str, str],
    ) -> tuple[list[dict[str, Any]], int, str | None]:
        wire_ns, project_uuid, importer_pv_uuid = shard
        try:
            rows, group_count = _fetch_importer_package_version_grouped_usage_rows(
                client,
                wire_ns,
                project_uuid,
                importer_pv_uuid,
                page_size=page_size,
                estate_root=estate_root,
                max_pages=max_pages,
            )
            return rows, group_count, None
        except Exception as exc:
            return (
                [],
                0,
                f"{namespace}/{project_uuid}/{importer_pv_uuid}: {exc}",
            )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_query_shard, shard) for shard in shards]
        for processed_shards, future in enumerate(as_completed(futures), start=1):
            rows, group_count, error = future.result()
            usage_rows.extend(rows)
            total_groups += group_count
            if error:
                errors.append(error)
            if progress_batch > 0 and processed_shards % progress_batch == 0:
                _emit_progress(processed_shards, len(shards), label="importer_pvs")

    _emit_progress(len(shards), len(shards), label="importer_pvs")
    return (
        usage_rows,
        total_groups,
        len(project_ids),
        len(shards),
        errors,
    )


def _result_from_usage_rows(
    estate_root: str,
    usage_rows: list[dict[str, Any]],
    *,
    namespace_count: int,
    project_count: int,
    importer_package_version_count: int,
    processed_groups: int,
    include_usage_detail: bool,
    raw_usage_rows: list[dict[str, Any]] | None = None,
) -> VersionCardinalityResult:
    _emit_progress(processed_groups, processed_groups, label="groups")
    rollup_rows = _rollup_version_cardinality(estate_root, usage_rows)
    max_cardinality = max(
        (int(row["version_cardinality"]) for row in rollup_rows), default=0
    )
    total_usage = sum(int(row["dependency_usage_rows"]) for row in rollup_rows)
    stats = VersionCardinalityStats(
        estate_root=estate_root,
        namespace_count=namespace_count,
        project_count=project_count,
        importer_package_version_count=importer_package_version_count,
        package_count=len(rollup_rows),
        name_version_group_count=len(usage_rows),
        max_version_cardinality=max_cardinality,
        total_dependency_usage_rows=total_usage,
    )
    message = (
        f"Version cardinality for {len(rollup_rows)} packages from "
        f"{len(usage_rows)} name-by-version groups "
        f"({namespace_count} namespace(s), {project_count} project(s), "
        f"{importer_package_version_count} importer package version(s))."
    )
    logger.info(message)
    detail_source = raw_usage_rows if raw_usage_rows is not None else usage_rows
    usage_table = (
        TabularExport(
            rows=_merge_usage_rows_by_project(estate_root, detail_source),
            columns=list(VERSION_USAGE_COLUMNS),
        )
        if include_usage_detail
        else TabularExport()
    )
    return VersionCardinalityResult(
        status="success",
        message=message,
        errors=[],
        stats=stats,
        table=TabularExport(
            rows=rollup_rows,
            columns=list(VERSION_CARDINALITY_COLUMNS),
        ),
        usage_by_name_version=usage_table,
    )


def export_version_cardinality(
    client: Client,
    estate_root: str,
    *,
    page_size: int | None = None,
    max_pages: int | None = None,
    progress_batch: int = _DEFAULT_PROGRESS_BATCH,
    max_project_workers: int = _DEFAULT_MAX_PROJECT_WORKERS,
    include_usage_detail: bool = False,
) -> VersionCardinalityResult:
    """Aggregate by package name + version; return version-cardinality rollup.

    Discovers namespaces with ``Namespace.list(traverse=True)``, lists projects
    and importer ``PackageVersion`` rows per namespace, runs grouped
    ``DependencyMetadata`` queries scoped to each importer
    ``spec.importer_data.package_version_uuid`` (``traverse=False``), and
    merges name-by-version counts before rollup.
    """
    page_size = page_size or _DEFAULT_PAGE_SIZE
    try:
        discovered = discover_estate_namespace_names(client, estate_root)
        namespace_names = namespaces_for_grouped_counts(
            discovered, estate_root=estate_root
        )
    except Exception as exc:
        return VersionCardinalityResult(
            status="error",
            message=f"Namespace list failed: {exc}",
            errors=[str(exc)],
            stats=VersionCardinalityStats(estate_root=estate_root),
        )

    total_namespaces = len(namespace_names)
    discovered_count = len(discovered)
    logger.info(
        "Fetching importer PackageVersion-scoped grouped DependencyMetadata "
        "(%s counting namespaces from %s discovered via Namespace traverse, "
        "aggregate by %s + %s, max_project_workers=%s)",
        total_namespaces,
        discovered_count,
        PACKAGE_NAME_PATH,
        PACKAGE_VERSION_PATH,
        max_project_workers,
    )

    raw_usage_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    total_groups = 0
    total_projects = 0
    total_importer_pvs = 0

    for index, ns in enumerate(namespace_names, start=1):
        _emit_progress(index, total_namespaces, label="namespaces")
        logger.info("Namespace %s (%s/%s)", ns, index, total_namespaces)
        (
            ns_rows,
            group_count,
            project_count,
            importer_pv_count,
            ns_errors,
        ) = _fetch_namespace_via_importer_package_versions(
            client,
            ns,
            estate_root,
            page_size=page_size,
            max_pages=max_pages,
            progress_batch=progress_batch,
            max_project_workers=max_project_workers,
        )
        raw_usage_rows.extend(ns_rows)
        total_groups += group_count
        total_projects += project_count
        total_importer_pvs += importer_pv_count
        errors.extend(ns_errors)

    if errors and not raw_usage_rows:
        return VersionCardinalityResult(
            status="error",
            message="Grouped DependencyMetadata list failed for all importer PVs",
            errors=errors,
            stats=VersionCardinalityStats(
                estate_root=estate_root,
                namespace_count=total_namespaces,
                project_count=total_projects,
                importer_package_version_count=total_importer_pvs,
            ),
        )

    usage_rows = _merge_usage_rows(estate_root, raw_usage_rows)
    result = _result_from_usage_rows(
        estate_root,
        usage_rows,
        namespace_count=total_namespaces,
        project_count=total_projects,
        importer_package_version_count=total_importer_pvs,
        processed_groups=total_groups,
        include_usage_detail=include_usage_detail,
        raw_usage_rows=raw_usage_rows,
    )
    if errors:
        result.errors = errors
        result.message = (
            f"{result.message} {len(errors)} importer PV query(ies) failed; "
            "counts reflect successful shards only."
        )
    return result


def export_version_cardinality_for_package_match(
    client: Client,
    estate_root: str,
    package_name_match: str,
    *,
    exact_package_name: str | None = None,
    page_size: int | None = None,
    max_pages: int | None = None,
    include_usage_detail: bool = False,
) -> VersionCardinalityResult:
    """Grouped DependencyMetadata per namespace with a ``package_name`` filter.

    Faster than full-estate PV sharding when analyzing one dependency coordinate
    family (for example ``jackson-databind`` substring → qualified Maven name).
    """
    page_size = page_size or _DEFAULT_PAGE_SIZE
    try:
        discovered = discover_estate_namespace_names(client, estate_root)
        namespace_names = namespaces_for_grouped_counts(
            discovered, estate_root=estate_root
        )
    except Exception as exc:
        return VersionCardinalityResult(
            status="error",
            message=f"Namespace list failed: {exc}",
            errors=[str(exc)],
            stats=VersionCardinalityStats(estate_root=estate_root),
        )

    list_params = grouped_count_list_parameters(page_size=page_size)
    list_params = list_params.model_copy(
        update={
            "filter": (
                f'spec.dependency_data.package_name.matches("{package_name_match}")'
            )
        }
    )

    raw_usage_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    total_groups = 0
    total_namespaces = len(namespace_names)

    logger.info(
        "Fetching package-filter grouped DependencyMetadata "
        "(%s namespaces, filter matches %r)",
        total_namespaces,
        package_name_match,
    )

    for index, ns in enumerate(namespace_names, start=1):
        _emit_progress(index, total_namespaces, label="namespaces")
        try:
            group_count = 0
            for bucket in _iter_group_buckets(
                client,
                ns,
                list_params,
                max_pages=max_pages,
            ):
                row = _usage_row_from_group(
                    estate_root,
                    bucket,
                    project_uuid="",
                )
                if row is None:
                    continue
                if exact_package_name and row["package_name"] != exact_package_name:
                    continue
                raw_usage_rows.append(row)
                group_count += 1
            total_groups += group_count
        except Exception as exc:
            errors.append(f"{ns}: {exc}")
            logger.warning("Package-filter grouped list failed for %s: %s", ns, exc)

    if errors and not raw_usage_rows:
        return VersionCardinalityResult(
            status="error",
            message="Grouped DependencyMetadata list failed for all namespaces",
            errors=errors,
            stats=VersionCardinalityStats(
                estate_root=estate_root,
                namespace_count=total_namespaces,
            ),
        )

    usage_rows = _merge_usage_rows(estate_root, raw_usage_rows)
    result = _result_from_usage_rows(
        estate_root,
        usage_rows,
        namespace_count=total_namespaces,
        project_count=0,
        importer_package_version_count=0,
        processed_groups=total_groups,
        include_usage_detail=include_usage_detail,
        raw_usage_rows=raw_usage_rows,
    )
    if errors:
        result.errors = errors
        result.message = (
            f"{result.message} {len(errors)} namespace(s) failed; "
            "counts reflect successful namespaces only."
        )
    return result


def _summary_dict(result: VersionCardinalityResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "message": result.message,
        "errors": result.errors,
        "estate_root": result.stats.estate_root,
        "namespace_count": result.stats.namespace_count,
        "project_count": result.stats.project_count,
        "importer_package_version_count": result.stats.importer_package_version_count,
        "package_count": result.stats.package_count,
        "name_version_group_count": result.stats.name_version_group_count,
        "max_version_cardinality": result.stats.max_version_cardinality,
        "total_dependency_usage_rows": result.stats.total_dependency_usage_rows,
        "version_cardinality_rows": result.table.row_count,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Build argparse parser for this workflow CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Export version cardinality for DependencyMetadata: distinct "
            "package versions in use per package name (server-side aggregate)."
        ),
    )
    parser.add_argument(
        "--namespace",
        "-n",
        default=os.environ.get("ENDOR_NAMESPACE"),
        help="Estate root namespace (default: ENDOR_NAMESPACE).",
    )
    parser.add_argument(
        "--output",
        "-o",
        help=(
            "Output CSV path for version-cardinality rollup "
            "(default: "
            f"{default_runs_dir('version-cardinality').as_posix()}/"
            "version_cardinality_<slug>.csv)."
        ),
    )
    parser.add_argument(
        "--usage-detail-output",
        help="Optional CSV for package_name and package_version usage rows.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Max grouped-list pages (default: unlimited).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=_DEFAULT_PAGE_SIZE,
        help=f"Grouped list page size (default: {_DEFAULT_PAGE_SIZE}).",
    )
    parser.add_argument(
        "--progress-batch",
        type=int,
        default=_DEFAULT_PROGRESS_BATCH,
        help=(
            "Emit progress every N importer PackageVersion shards within a "
            f"namespace (default: {_DEFAULT_PROGRESS_BATCH})."
        ),
    )
    parser.add_argument(
        "--max-project-workers",
        type=int,
        default=_DEFAULT_MAX_PROJECT_WORKERS,
        help=(
            "Concurrent importer PackageVersion grouped queries per namespace "
            f"(default: {_DEFAULT_MAX_PROJECT_WORKERS})."
        ),
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=None,
        help=(
            "HTTP read timeout in seconds for grouped list pages "
            f"(default: ENDOR_REQUEST_TIMEOUT or {_DEFAULT_GROUPED_REQUEST_TIMEOUT:g})."
        ),
    )
    parser.add_argument(
        "--package-name-match",
        help=(
            "Substring/regex filter on spec.dependency_data.package_name "
            "(estate-wide per-namespace grouped query; faster for one package)."
        ),
    )
    parser.add_argument(
        "--exact-package-name",
        help=(
            "After --package-name-match, keep only this qualified package_name "
            "(optional)."
        ),
    )
    parser.add_argument(
        "--remediation-cve",
        help=(
            "Compare as-is vs intra-minor-flattened upgrade paths for a CVE "
            "(requires usage rows; uses --usage-detail-output or rollup scope)."
        ),
    )
    parser.add_argument(
        "--remediation-output",
        help="Write remediation comparison JSON (use with --remediation-cve).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI: grouped aggregate export and CSV write."""
    _configure_cli_logging()
    args = parse_args(argv)
    if not args.namespace:
        sys.stderr.write("error: --namespace or ENDOR_NAMESPACE is required\n")
        return 2

    if args.output:
        output_path = Path(args.output)
    else:
        from endorlabs.workflows.estate.analyze.compile_graph.pipeline import (
            namespace_slug,
        )

        slug = namespace_slug(args.namespace)
        output_path = (
            default_runs_dir("version-cardinality") / f"version_cardinality_{slug}.csv"
        )
    request_timeout = _resolve_request_timeout(args.request_timeout)
    remediation: RemediationComparisonResult | None = None
    with endorlabs.Client(tenant=args.namespace, timeout=request_timeout) as client:
        if args.package_name_match:
            result = export_version_cardinality_for_package_match(
                client,
                args.namespace,
                args.package_name_match,
                exact_package_name=args.exact_package_name,
                page_size=args.page_size,
                max_pages=args.max_pages,
                include_usage_detail=bool(
                    args.usage_detail_output or args.remediation_cve
                ),
            )
        else:
            result = export_version_cardinality(
                client,
                args.namespace,
                page_size=args.page_size,
                max_pages=args.max_pages,
                progress_batch=args.progress_batch,
                max_project_workers=args.max_project_workers,
                include_usage_detail=bool(
                    args.usage_detail_output or args.remediation_cve
                ),
            )
        if args.remediation_cve and result.ok:
            usage_rows = (
                result.usage_by_name_version.rows
                if result.usage_by_name_version.row_count
                else result.table.rows
            )
            package_name = args.exact_package_name or ""
            if not package_name and len(result.table.rows) == 1:
                package_name = str(result.table.rows[0].get("package_name") or "")
            remediation = analyze_intra_minor_remediation(
                usage_rows,
                cve_id=args.remediation_cve,
                package_name=package_name,
            )

    if result.ok:
        write_table(result.table, output_path)
        if args.usage_detail_output and result.usage_by_name_version.row_count:
            write_table(result.usage_by_name_version, args.usage_detail_output)

    summary = _summary_dict(result)
    if result.ok:
        summary["output"] = str(output_path)
        if args.usage_detail_output:
            summary["usage_detail_output"] = args.usage_detail_output
    if remediation is not None:
        summary["remediation"] = remediation.to_dict()
        if args.remediation_output:
            remediation_path = Path(args.remediation_output)
            safe_write_text(
                remediation_path.parent,
                remediation_path,
                json.dumps(remediation.to_dict(), indent=2) + "\n",
            )
            summary["remediation_output"] = args.remediation_output
    sys.stdout.write(json.dumps(summary, indent=2) + "\n")
    return 0 if result.ok else 1
