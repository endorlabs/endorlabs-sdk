"""Column presets for analytics version-cardinality exports."""

from __future__ import annotations

# Server-side group keys (DependencyMetadata dependency_data fields).
PACKAGE_NAME_PATH = "spec.dependency_data.package_name"
PACKAGE_VERSION_PATH = "spec.dependency_data.resolved_version"

VERSION_CARDINALITY_COLUMNS: tuple[str, ...] = (
    "estate_root",
    "package_name",
    "version_cardinality",
    "dependency_usage_rows",
)

VERSION_USAGE_COLUMNS: tuple[str, ...] = (
    "estate_root",
    "project_uuid",
    "package_name",
    "package_version",
    "usage_count",
)
