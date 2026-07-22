"""Column presets for the patch-fixable-findings report."""

from __future__ import annotations

PATCH_FIX_REPORT_COLUMNS: tuple[str, ...] = (
    "namespace",
    "package_name",
    "current_version",
    "patch_version",
    "finding_count",
    "distinct_patch_version_count",
    "distinct_upgrade_path_count",
    "project_count",
)

PATCH_FIX_FINDING_DETAIL_COLUMNS: tuple[str, ...] = (
    "namespace",
    "project_uuid",
    "finding_uuid",
    "finding_type_name",
    "vuln_id",
    "vuln_aliases",
    "vuln_summary",
    "severity",
    "package_name",
    "current_version",
    "patch_version",
    "target_dependency_package_name",
    "target_dependency_version",
    "endor_patch_available",
    "fix_available",
    "patch_status",
    "reachable_function",
    "potentially_reachable_function",
    "upgrade_risk",
)
