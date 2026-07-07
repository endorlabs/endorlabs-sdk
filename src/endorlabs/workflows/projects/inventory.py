"""Tenant project and installation inventory helpers for workflows and skills."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

from endorlabs.tools.list_sharding import (
    ProjectShard,
    parallel_map_shards,
)
from endorlabs.workflows.wire_access import dict_str, nested_dict, nested_str

if TYPE_CHECKING:
    from endorlabs import Client

INSTALLATION_LIST_MASK = (
    "meta.name,tenant_meta.namespace,uuid,"
    "spec.external_id,spec.external_name,spec.login"
)

PROJECT_SHARD_MASK = "meta.name,tenant_meta.namespace,uuid,spec.sbom"

SCAN_EXECUTION_MASK = "spec.environment.config.RunBySystem,meta.create_time"

REGISTRATION_SOURCE_CLOUD = "Cloud Scan"
REGISTRATION_SOURCE_CLI = "CLI"
SCAN_EXECUTION_UNKNOWN = "unknown"


def build_installation_lookup(
    installations: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Map ``Installation.spec.external_id`` to installation dict rows."""
    lookup: dict[str, dict[str, Any]] = {}
    for row in installations:
        ext_id = nested_str(nested_dict(row, "spec"), "external_id")
        if ext_id:
            lookup[ext_id] = row
    return lookup


def installation_display_name(installation: dict[str, Any] | None) -> str:
    """Resolve a human-readable installation label for CSV or summaries."""
    if not installation:
        return ""
    spec = nested_dict(installation, "spec")
    meta_name = nested_str(installation, "meta", "name")
    external_name = dict_str(spec, "external_name")
    login = dict_str(spec, "login")
    if external_name:
        return external_name
    if meta_name and login:
        return f"{meta_name} ({login})"
    return meta_name or login


def fetch_installation_lookup(
    client: Client,
    *,
    traverse: bool = True,
    mask: str = INSTALLATION_LIST_MASK,
    max_pages: int | None = None,
) -> dict[str, dict[str, Any]]:
    """List installations tenant-wide and return an external_id lookup map."""
    kwargs: dict[str, Any] = {"traverse": traverse, "mask": mask}
    if max_pages is not None:
        kwargs["max_pages"] = max_pages
    rows = list(client.Installation.list_iter(**kwargs))
    return build_installation_lookup(rows)


def _project_uuid(row: Any) -> str:
    if isinstance(row, dict):
        return dict_str(cast("dict[str, Any]", row), "uuid")
    return str(getattr(row, "uuid", None) or "")


def discover_tenant_project_shards(
    client: Client,
    tenant: str,
    *,
    max_pages: int | None = None,
    exclude_sbom: bool = True,
) -> list[ProjectShard]:
    """Discover non-SBOM projects for parallel tenant-wide list shards."""
    return client.Query.Project.discover(
        tenant,
        traverse=True,
        max_pages=max_pages,
        exclude_sbom=exclude_sbom,
    ).project_shards()


def registration_source_label(client: Client, row: Any) -> str:
    """Classify project registration: SCM app installation vs CLI."""
    if client.Project.is_app(row):
        return REGISTRATION_SOURCE_CLOUD
    return REGISTRATION_SOURCE_CLI


def extract_run_by_system(scan_row: Any) -> bool | None:
    """Read ``ScanResult.spec.environment.config.RunBySystem`` when present."""
    if isinstance(scan_row, dict):
        scan_dict = cast("dict[str, Any]", scan_row)
        config = nested_dict(
            nested_dict(nested_dict(scan_dict, "spec"), "environment"), "config"
        )
        value = config.get("RunBySystem")
        if value is None:
            return None
        return bool(value)

    spec = getattr(scan_row, "spec", None)
    environment = getattr(spec, "environment", None) if spec is not None else None
    config = getattr(environment, "config", None) if environment is not None else None
    if config is None:
        return None
    if isinstance(config, dict):
        config_dict = cast("dict[str, Any]", config)
        value = config_dict.get("RunBySystem")
    else:
        value = getattr(config, "RunBySystem", None)
    if value is None:
        return None
    return bool(value)


def scan_execution_label(run_by_system: bool | None) -> str:
    """Map ``RunBySystem`` to a CLI vs Cloud Scan execution label."""
    if run_by_system is True:
        return REGISTRATION_SOURCE_CLOUD
    if run_by_system is False:
        return REGISTRATION_SOURCE_CLI
    return SCAN_EXECUTION_UNKNOWN


def latest_scan_execution_label(client: Client, project_row: Any) -> str:
    """Return latest scan execution label for *project_row* (one newest ScanResult)."""
    scans = client.ScanResult.list_by_project(
        project_row,
        mask=SCAN_EXECUTION_MASK,
        limit=1,
    )
    if not scans:
        return SCAN_EXECUTION_UNKNOWN
    return scan_execution_label(extract_run_by_system(scans[0]))


def fetch_latest_scan_execution_labels(
    client: Client,
    projects: Sequence[Any],
    *,
    max_workers: int = 12,
) -> dict[str, str]:
    """Parallel lookup of latest scan execution labels keyed by project UUID."""
    by_uuid = {_project_uuid(row): row for row in projects if _project_uuid(row)}
    if not by_uuid:
        return {}

    shards = [
        ProjectShard(project_uuid=uuid, namespace="", label=None) for uuid in by_uuid
    ]

    def _worker(shard: ProjectShard) -> tuple[str, str]:
        row = by_uuid[shard.project_uuid]
        return shard.project_uuid, latest_scan_execution_label(client, row)

    return dict(
        parallel_map_shards(
            shards,
            _worker,
            max_workers=max_workers,
            progress_label="latest scan execution",
        )
    )


def is_mixed_registration_execution(registration: str, execution: str) -> bool:
    """True when registration and latest scan execution disagree (both known)."""
    if execution == SCAN_EXECUTION_UNKNOWN:
        return False
    return registration != execution
