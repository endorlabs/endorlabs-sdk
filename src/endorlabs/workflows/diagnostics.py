"""Diagnostic workflows: scan log comparison, dependency reports.

Provides composable functions for inspecting scan results, comparing
scan logs across runs, and auditing dependency visibility.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .common import WorkflowResult

if TYPE_CHECKING:
    from endorlabs import Client

from endorlabs.utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ScanLogEntry:
    """A single scan run's metadata and log messages."""

    scan_result_uuid: str = ""
    status: str = ""
    exit_code: int | None = None
    start_time: str = ""
    end_time: str = ""
    log_messages: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ScanLogComparison(WorkflowResult):
    """Result of comparing multiple scan runs."""

    entries: list[ScanLogEntry] = field(default_factory=list)
    num_scans_requested: int = 0
    num_scans_found: int = 0


@dataclass
class DependencyStats:
    """Aggregated statistics about dependencies."""

    total: int = 0
    by_namespace: dict[str, int] = field(default_factory=dict)
    by_ecosystem: dict[str, int] = field(default_factory=dict)
    by_scope: dict[str, int] = field(default_factory=dict)
    by_reachability: dict[str, int] = field(default_factory=dict)
    unique_packages: int = 0
    unique_importers: int = 0


@dataclass
class DependencyReport(WorkflowResult):
    """Result of listing project dependencies."""

    stats: DependencyStats = field(default_factory=DependencyStats)
    dependencies: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class VisibilityStats:
    """Aggregated visibility statistics."""

    total: int = 0
    public: int = 0
    private: int = 0
    unknown: int = 0
    by_ecosystem: dict[str, int] = field(default_factory=dict)


@dataclass
class VisibilityReport(WorkflowResult):
    """Result of checking dependency visibility."""

    stats: VisibilityStats = field(default_factory=VisibilityStats)


# ---------------------------------------------------------------------------
# Compare scan logs
# ---------------------------------------------------------------------------


def compare_scan_logs(
    client: Client,
    namespace: str,
    project_uuid: str,
    *,
    num_scans: int = 2,
    log_levels: list[str] | None = None,
    traverse: bool = False,
) -> ScanLogComparison:
    """Compare the last N scan results and their logs for a project.

    Fetches recent ``ScanResult`` resources and retrieves logs via
    ``client.scan_logs.get_logs()``.

    Args:
        client: Authenticated ``endorlabs.Client`` instance.
        namespace: Namespace to query.
        project_uuid: Project UUID to filter scan results.
        num_scans: Number of recent scans to compare.
        log_levels: Log levels to include (e.g. ``["ERROR", "WARNING"]``).
            Defaults to ERROR and WARNING.
        traverse: When True, traverse child namespaces.

    Returns:
        ScanLogComparison with entries for each scan.
    """
    from endorlabs.resources.scan_log_request import ScanLogLevel

    result = ScanLogComparison(num_scans_requested=num_scans)

    # Fetch recent scan results
    from endorlabs.filter import F

    scan_results = client.scan_result.list(
        namespace=namespace,
        filter=F("meta.parent_uuid") == project_uuid,
        sort_by="meta.create_time",
        desc=True,
        page_size=num_scans,
        max_pages=1,
        traverse=traverse,
    )

    result.num_scans_found = len(scan_results)
    if not scan_results:
        result.message = f"No scan results found for project {project_uuid}."
        return result

    # Resolve log levels
    level_map = {
        "ERROR": ScanLogLevel.ERROR,
        "WARNING": ScanLogLevel.WARNING,
        "INFO": ScanLogLevel.INFO,
        "DEBUG": ScanLogLevel.DEBUG,
        "CRITICAL": ScanLogLevel.CRITICAL,
        "ALERT": ScanLogLevel.ALERT,
        "EMERGENCY": ScanLogLevel.EMERGENCY,
        "NOTICE": ScanLogLevel.NOTICE,
    }
    if log_levels:
        resolved_levels = [
            level_map[lv.upper()] for lv in log_levels if lv.upper() in level_map
        ]
    else:
        resolved_levels = [ScanLogLevel.ERROR, ScanLogLevel.WARNING]

    for sr in scan_results[:num_scans]:
        entry = ScanLogEntry(
            scan_result_uuid=sr.uuid,
            status=str(sr.spec.status) if sr.spec and sr.spec.status else "",
            exit_code=sr.spec.exit_code if sr.spec else None,
            start_time=str(sr.spec.start_time)
            if sr.spec and sr.spec.start_time
            else "",
            end_time=str(sr.spec.end_time) if sr.spec and sr.spec.end_time else "",
        )

        try:
            logs = client.scan_logs.get_logs(
                sr.uuid,
                namespace=namespace,
                log_levels=resolved_levels,
            )
            entry.log_messages = [
                {
                    "level": str(msg.level) if msg.level else "",
                    "timestamp": msg.timestamp or "",
                    "payload": msg.json_payload or {},
                }
                for msg in logs
            ]
        except Exception as exc:
            logger.warning("Unable to fetch logs for '%s': %s", sr.uuid, exc)
            entry.log_messages = [{"error": str(exc)}]

        result.entries.append(entry)

    result.message = f"Compared {len(result.entries)}/{num_scans} scan(s)."
    return result


# ---------------------------------------------------------------------------
# List project dependencies
# ---------------------------------------------------------------------------


def list_project_dependencies(
    client: Client,
    namespace: str,
    *,
    traverse: bool = True,
) -> DependencyReport:
    """List all dependency metadata across namespaces.

    Uses ``client.dependency_metadata.list()`` with traverse to query
    all DependencyMetadata resources.

    Args:
        client: Authenticated ``endorlabs.Client`` instance.
        namespace: Root namespace to query from.
        traverse: When True, include child namespaces.

    Returns:
        DependencyReport with statistics and formatted dependency list.
    """
    deps = client.dependency_metadata.list(namespace=namespace, traverse=traverse)

    stats = DependencyStats(total=len(deps))
    ns_counts: dict[str, int] = defaultdict(int)
    eco_counts: dict[str, int] = defaultdict(int)
    scope_counts: dict[str, int] = defaultdict(int)
    reach_counts: dict[str, int] = defaultdict(int)
    packages: set[str] = set()
    importers: set[str] = set()

    formatted: list[dict[str, Any]] = []

    for dep in deps:
        ns_name = (
            dep.tenant_meta.namespace
            if dep.tenant_meta and dep.tenant_meta.namespace
            else "unknown"
        )
        ns_counts[ns_name] += 1

        dep_data = dep.spec.dependency_data if dep.spec else None
        importer_data = dep.spec.importer_data if dep.spec else None

        entry: dict[str, Any] = {"uuid": dep.uuid, "namespace": ns_name}

        if dep_data:
            packages.add(dep_data.package_name or "")
            eco = str(dep_data.ecosystem.value) if dep_data.ecosystem else "unknown"
            eco_counts[eco] += 1
            if dep_data.scope:
                scope_counts[str(dep_data.scope.value)] += 1
            if dep_data.reachability:
                reach_counts[str(dep_data.reachability.value)] += 1
            entry["dependency"] = {
                "package_name": dep_data.package_name,
                "resolved_version": dep_data.resolved_version,
                "ecosystem": eco,
            }

        if importer_data:
            importers.add(importer_data.package_name or "")
            entry["importer"] = {"package_name": importer_data.package_name}

        formatted.append(entry)

    stats.by_namespace = dict(ns_counts)
    stats.by_ecosystem = dict(eco_counts)
    stats.by_scope = dict(scope_counts)
    stats.by_reachability = dict(reach_counts)
    stats.unique_packages = len(packages - {""})
    stats.unique_importers = len(importers - {""})

    return DependencyReport(
        stats=stats,
        dependencies=formatted,
        message=(
            f"Found {stats.total} dependencies"
            f" ({stats.unique_packages} unique packages)."
        ),
    )


# ---------------------------------------------------------------------------
# Check dependency visibility
# ---------------------------------------------------------------------------


def check_dependency_visibility(
    client: Client,
    namespace: str,
    *,
    filter_public: bool | None = None,
    traverse: bool = True,
) -> VisibilityReport:
    """Check dependency visibility (public/private) across namespaces.

    Args:
        client: Authenticated ``endorlabs.Client`` instance.
        namespace: Root namespace to query from.
        filter_public: When True, only return public deps. When False,
            only private. When None, return all.
        traverse: When True, include child namespaces.

    Returns:
        VisibilityReport with aggregated visibility statistics.
    """
    list_kwargs: dict[str, Any] = {
        "namespace": namespace,
        "traverse": traverse,
    }
    if filter_public is not None:
        list_kwargs["filter"] = (
            f"spec.dependency_data.public=={str(filter_public).lower()}"
        )

    deps = client.dependency_metadata.list(**list_kwargs)

    stats = VisibilityStats(total=len(deps))
    eco_counts: dict[str, int] = defaultdict(int)

    for dep in deps:
        dep_data = dep.spec.dependency_data if dep.spec else None
        if dep_data:
            dep_dict = dep_data.model_dump() if hasattr(dep_data, "model_dump") else {}
            public_value = dep_dict.get("public")
            if public_value is True:
                stats.public += 1
            elif public_value is False:
                stats.private += 1
            else:
                stats.unknown += 1

            eco = str(dep_data.ecosystem.value) if dep_data.ecosystem else "unknown"
            eco_counts[eco] += 1

    stats.by_ecosystem = dict(eco_counts)

    return VisibilityReport(
        stats=stats,
        message=(
            f"Visibility: {stats.public} public, {stats.private} private, "
            f"{stats.unknown} unknown (total={stats.total})."
        ),
    )
