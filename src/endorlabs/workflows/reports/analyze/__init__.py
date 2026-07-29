"""Report analysis layer (Client in → structured dict out)."""

from __future__ import annotations

from endorlabs.workflows.reports.analyze import (
    auth_credential_expiry,
    auth_login_count,
    auth_policies_audit,
    ci_endorctl_audit,
    cli_vs_cloud,
    duplicate_projects,
    findings_chart_analysis,
    prf_report_analysis,
)
from endorlabs.workflows.reports.analyze.projects import (
    build_onboarding_report,
    discover_projects,
    normalize_project_row,
    path_options_from_namespaces,
)

__all__ = [
    "auth_credential_expiry",
    "auth_login_count",
    "auth_policies_audit",
    "build_onboarding_report",
    "ci_endorctl_audit",
    "cli_vs_cloud",
    "discover_projects",
    "duplicate_projects",
    "findings_chart_analysis",
    "normalize_project_row",
    "path_options_from_namespaces",
    "prf_report_analysis",
]
