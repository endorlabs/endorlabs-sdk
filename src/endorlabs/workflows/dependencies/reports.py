"""Dependency listing and visibility reporting."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any, cast

from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.wire_access import (
    dict_str,
    model_to_dict,
    nested_dict,
    nested_str,
)

from .types import (
    DependencyReport,
    DependencyStats,
    VisibilityReport,
    VisibilityStats,
)

if TYPE_CHECKING:
    from endorlabs import Client

logger = get_resource_logger(__name__)


def _wire_field_str(d: dict[str, Any], key: str, *, default: str = "unknown") -> str:
    raw = d.get(key)
    if raw is None:
        return default
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        return dict_str(cast("dict[str, Any]", raw), "value", default)
    val = getattr(raw, "value", raw)
    return str(val) if val is not None else default


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
        dep_wire = model_to_dict(dep)
        ns_name = nested_str(dep_wire, "tenant_meta", "namespace") or "unknown"
        ns_counts[ns_name] += 1

        spec = nested_dict(dep_wire, "spec")
        dep_data = nested_dict(spec, "dependency_data")
        importer_data = nested_dict(spec, "importer_data")

        entry: dict[str, Any] = {
            "uuid": dict_str(dep_wire, "uuid"),
            "namespace": ns_name,
        }

        if dep_data:
            package_name = dict_str(dep_data, "package_name")
            packages.add(package_name)
            eco = _wire_field_str(dep_data, "ecosystem")
            eco_counts[eco] += 1
            scope = _wire_field_str(dep_data, "scope", default="")
            if scope:
                scope_counts[scope] += 1
            reachability = _wire_field_str(dep_data, "reachability", default="")
            if reachability:
                reach_counts[reachability] += 1
            entry["dependency"] = {
                "package_name": package_name,
                "resolved_version": dict_str(dep_data, "resolved_version"),
                "ecosystem": eco,
            }

        if importer_data:
            importer_name = dict_str(importer_data, "package_name")
            importers.add(importer_name)
            entry["importer"] = {"package_name": importer_name}

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
        dep_wire = model_to_dict(dep)
        spec = nested_dict(dep_wire, "spec")
        dep_data = nested_dict(spec, "dependency_data")
        if dep_data:
            public_value = dep_data.get("public")
            if public_value is True:
                stats.public += 1
            elif public_value is False:
                stats.private += 1
            else:
                stats.unknown += 1

            eco = _wire_field_str(dep_data, "ecosystem")
            eco_counts[eco] += 1

    stats.by_ecosystem = dict(eco_counts)

    return VisibilityReport(
        stats=stats,
        message=(
            f"Visibility: {stats.public} public, {stats.private} private, "
            f"{stats.unknown} unknown (total={stats.total})."
        ),
    )
