"""Estate workspace resource registry — collect artifacts aligned to API resources."""

from __future__ import annotations

from typing import Literal

WORKSPACE_COLLECT_SCHEMA = "endor.workspace_collect.v1"
COLLECT_MANIFEST_FILENAME = "collect_manifest.json"
DATA_DIR = "data"
IR_DIR = "intermediate-representation"
VIZ_DIR = "viz"
LOGS_DIR = "logs"
PULL_LOG_FILENAME = "pull.log"
ANALYZE_LOG_FILENAME = "analyze.log"

ResourceStatus = Literal["pending", "partial", "complete", "failed"]

RESOURCE_PROJECT = "project"
RESOURCE_DEPENDENCY_METADATA = "dependency_metadata"
RESOURCE_FINDING = "finding"
RESOURCE_PACKAGE_VERSION = "package_version"

COLLECT_RESOURCE_IDS: frozenset[str] = frozenset(
    {
        RESOURCE_PROJECT,
        RESOURCE_DEPENDENCY_METADATA,
        RESOURCE_FINDING,
        RESOURCE_PACKAGE_VERSION,
    }
)

RESOURCE_ARTIFACT_FILENAMES: dict[str, str] = {
    RESOURCE_PROJECT: "project.jsonl",
    RESOURCE_DEPENDENCY_METADATA: "dependency_metadata.jsonl",
    RESOURCE_FINDING: "finding.jsonl",
    RESOURCE_PACKAGE_VERSION: "package_version.jsonl",
}

RESOURCE_ARTIFACT_SCHEMAS: dict[str, str] = {
    RESOURCE_PROJECT: "endor.workspace_resource.project.v1",
    RESOURCE_DEPENDENCY_METADATA: "endor.workspace_resource.dependency_metadata.v1",
    RESOURCE_FINDING: "endor.workspace_resource.finding.v1",
    RESOURCE_PACKAGE_VERSION: "endor.workspace_resource.package_version.v1",
}

SHARDED_RESOURCES: frozenset[str] = frozenset(
    {RESOURCE_DEPENDENCY_METADATA, RESOURCE_FINDING}
)


def resource_data_relpath(resource_id: str) -> str:
    """Relative artifact path under workspace root for a collect resource."""
    if resource_id not in RESOURCE_ARTIFACT_FILENAMES:
        msg = f"Unknown resource id {resource_id!r}"
        raise ValueError(msg)
    return f"{DATA_DIR}/{RESOURCE_ARTIFACT_FILENAMES[resource_id]}"


def collect_manifest_relpath() -> str:
    return f"{DATA_DIR}/{COLLECT_MANIFEST_FILENAME}"


def ir_relpath(filename: str) -> str:
    return f"{IR_DIR}/{filename}"


def viz_relpath(filename: str) -> str:
    return f"{VIZ_DIR}/{filename}"


def logs_relpath(filename: str) -> str:
    return f"{LOGS_DIR}/{filename}"
