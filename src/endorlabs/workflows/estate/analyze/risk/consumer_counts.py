"""Distinct consumer (project) counts per dependency version."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from endorlabs.filters import main_context_filter
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.estate.analyze.risk.scoring import dm_package_name_for_key
from endorlabs.workflows.estate.collect.namespaces import list_estate_namespace_names

if TYPE_CHECKING:
    from endorlabs import Client

logger = get_resource_logger(__name__)

_DM_CONSUMER_MASK = (
    "spec.importer_data.project_uuid,"
    "spec.dependency_data.resolved_version,"
    "spec.dependency_data.unresolved_version"
)


def _spec_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        spec = row.get("spec")
        return spec if isinstance(spec, dict) else {}
    spec = getattr(row, "spec", None)
    if spec is None:
        return {}
    if hasattr(spec, "model_dump"):
        dumped = spec.model_dump(mode="json", warnings=False)
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _project_uuid_from_row(row: Any) -> str:
    spec = _spec_dict(row)
    importer = spec.get("importer_data")
    if isinstance(importer, dict):
        raw = importer.get("project_uuid")
        if raw:
            return str(raw)
    return ""


def _version_from_row(row: Any) -> str:
    spec = _spec_dict(row)
    dep = spec.get("dependency_data")
    if not isinstance(dep, dict):
        return ""
    resolved = dep.get("resolved_version")
    if resolved:
        return str(resolved)
    unresolved = dep.get("unresolved_version")
    return str(unresolved or "")


def collect_consumer_counts_by_version(
    client: Client,
    estate_root: str,
    package_key: str,
    *,
    page_size: int = 500,
    max_pages: int | None = None,
) -> dict[str, int]:
    """Count distinct importer projects per resolved version for one package family."""
    dm_name = dm_package_name_for_key(package_key)
    filt = main_context_filter(f'spec.dependency_data.package_name=="{dm_name}"')
    consumers: dict[str, set[str]] = defaultdict(set)

    for namespace in list_estate_namespace_names(client, estate_root):
        rows = client.DependencyMetadata.list(
            filter=filt,
            namespace=namespace,
            mask=_DM_CONSUMER_MASK,
            page_size=page_size,
            max_pages=max_pages,
        )
        for row in rows:
            project_uuid = _project_uuid_from_row(row)
            version = _version_from_row(row)
            if not project_uuid or not version:
                continue
            consumers[version].add(project_uuid)

    return {version: len(projects) for version, projects in consumers.items()}


def merge_version_usage_and_consumers(
    usage_by_version: dict[str, int],
    consumers_by_version: dict[str, int],
) -> list[dict[str, Any]]:
    """Merge usage and consumer maps into rows sorted by consumer count descending."""
    all_versions = set(usage_by_version) | set(consumers_by_version)
    rows: list[dict[str, Any]] = []
    for version in all_versions:
        rows.append(
            {
                "version": version,
                "consumer_count": consumers_by_version.get(version, 0),
                "usage_count": usage_by_version.get(version, 0),
            }
        )
    rows.sort(
        key=lambda item: (
            -item["consumer_count"],
            -item["usage_count"],
            item["version"],
        )
    )
    return rows
