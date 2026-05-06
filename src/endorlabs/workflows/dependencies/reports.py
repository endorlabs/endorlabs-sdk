"""Dependency listing and visibility reporting."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from endorlabs.utils.logging_config import get_resource_logger

from .types import (
    DependencyReport,
    DependencyStats,
    VisibilityReport,
    VisibilityStats,
)

if TYPE_CHECKING:
    from endorlabs import Client

logger = get_resource_logger(__name__)


def list_project_dependencies(
    client: Client,
    namespace: str,
    *,
    traverse: bool = True,
) -> DependencyReport:
    """List all dependency metadata across namespaces.

    Uses ``client.DependencyMetadata.list()`` with traverse to query
    all DependencyMetadata resources.
    """
    deps = client.DependencyMetadata.list(namespace=namespace, traverse=traverse)

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


def check_dependency_visibility(
    client: Client,
    namespace: str,
    *,
    filter_public: bool | None = None,
    traverse: bool = True,
) -> VisibilityReport:
    """Check dependency visibility (public/private) across namespaces."""
    list_kwargs: dict[str, Any] = {
        "namespace": namespace,
        "traverse": traverse,
    }
    if filter_public is not None:
        list_kwargs["filter"] = (
            f"spec.dependency_data.public=={str(filter_public).lower()}"
        )

    deps = client.DependencyMetadata.list(**list_kwargs)

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
