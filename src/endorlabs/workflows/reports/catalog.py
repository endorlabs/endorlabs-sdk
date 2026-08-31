"""Report subcommand catalog for ``endor-reports`` CLI help and ``list``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from endorlabs.context.paths import (
    default_reports_subdir,
    flat_task_dir,
    reports_dir,
)

ReportCategory = Literal[
    "Executive",
    "Auth",
    "Inventory",
    "Analysis",
    "Maintainer",
]


@dataclass(frozen=True, slots=True)
class ReportCatalogEntry:
    """One row in the endor-reports report picker."""

    category: ReportCategory
    subcommand: str | None
    summary: str
    default_output: str
    deprecated: bool = False


def _reports_suffix_path(suffix: str) -> str:
    return f"{reports_dir().as_posix()}/{suffix}"


def _reports_subdir_path(subcommand: str) -> str:
    return f"{default_reports_subdir(subcommand).as_posix()}/"


REPORT_CATALOG: tuple[ReportCatalogEntry, ...] = (
    ReportCatalogEntry(
        category="Executive",
        subcommand=None,
        summary="Executive HTML packet (default when no subcommand)",
        default_output=_reports_suffix_path("<slug>-<YYYY-MM-DD>/"),
    ),
    ReportCatalogEntry(
        category="Executive",
        subcommand="build",
        summary="Executive HTML packet (explicit)",
        default_output=_reports_suffix_path("<slug>-<YYYY-MM-DD>/"),
    ),
    ReportCatalogEntry(
        category="Executive",
        subcommand="patches",
        summary="Endor Patches executive page only",
        default_output=_reports_suffix_path("patches/<slug>-<YYYY-MM-DD>/"),
    ),
    ReportCatalogEntry(
        category="Executive",
        subcommand="refresh-code",
        summary="Refresh SAST/AI-SAST/Secrets burndown in existing packet dir",
        default_output="in-place under --packet-dir",
    ),
    ReportCatalogEntry(
        category="Executive",
        subcommand="packet",
        summary="(deprecated) Executive HTML packet",
        default_output=_reports_suffix_path("<slug>-<YYYY-MM-DD>/"),
        deprecated=True,
    ),
    ReportCatalogEntry(
        category="Auth",
        subcommand="login-count",
        summary="AuthenticationLog login counts by identity",
        default_output=_reports_subdir_path("auth-login-count"),
    ),
    ReportCatalogEntry(
        category="Auth",
        subcommand="credential-expiry",
        summary="API key / credential expiry horizon",
        default_output=_reports_subdir_path("auth-credential-expiry"),
    ),
    ReportCatalogEntry(
        category="Auth",
        subcommand="auth-policies",
        summary="AuthorizationPolicy claim / namespace form audit",
        default_output=_reports_subdir_path("auth-policies"),
    ),
    ReportCatalogEntry(
        category="Inventory",
        subcommand="duplicates",
        summary="Duplicate project registrations",
        default_output=_reports_subdir_path("duplicates"),
    ),
    ReportCatalogEntry(
        category="Inventory",
        subcommand="cli-vs-cloud",
        summary="CLI-scanned vs cloud-integrated projects",
        default_output=_reports_subdir_path("cli-vs-cloud"),
    ),
    ReportCatalogEntry(
        category="Inventory",
        subcommand="ci-endorctl",
        summary="CI endorctl versions from latest CLI scans",
        default_output=_reports_subdir_path("ci-endorctl"),
    ),
    ReportCatalogEntry(
        category="Analysis",
        subcommand="findings-trend",
        summary="FindingLog weekly new-vs-resolved chart",
        default_output=_reports_subdir_path("findings-trend"),
    ),
    ReportCatalogEntry(
        category="Analysis",
        subcommand="prf-analysis",
        summary="Potentially reachable findings + PV resolution errors",
        default_output=_reports_subdir_path("prf-analysis"),
    ),
    ReportCatalogEntry(
        category="Analysis",
        subcommand="package-resolution",
        summary="PackageVersion resolution CSV + interactive HTML",
        default_output=_reports_subdir_path("package-resolution"),
    ),
    ReportCatalogEntry(
        category="Maintainer",
        subcommand="parity",
        summary="Compare packet cube to scratch baseline JSON",
        default_output=f"{flat_task_dir('parity').as_posix()}/<slug>-<YYYY-MM-DD>/",
    ),
)


def catalog_epilog() -> str:
    """Grouped subcommand list for ``--help`` epilog."""
    lines = [
        "Report subcommands (use `endor-reports list` for full catalog):",
        "",
    ]
    current: ReportCategory | None = None
    for entry in REPORT_CATALOG:
        if entry.deprecated:
            continue
        if entry.category != current:
            current = entry.category
            lines.append(f"{current}:")
        label = entry.subcommand or "(default build)"
        lines.append(f"  {label:22} {entry.summary}")
    lines.append("")
    lines.append("Set namespace via -n or --namespace; ENDOR_NAMESPACE fallback.")
    return "\n".join(lines)


def catalog_for_list(*, include_deprecated: bool = False) -> list[dict[str, str]]:
    """Serialize catalog rows for ``endor-reports list --json``."""
    rows: list[dict[str, str]] = []
    for entry in REPORT_CATALOG:
        if entry.deprecated and not include_deprecated:
            continue
        rows.append(
            {
                "category": entry.category,
                "subcommand": entry.subcommand or "",
                "summary": entry.summary,
                "default_output": entry.default_output,
                "deprecated": str(entry.deprecated).lower(),
            }
        )
    return rows
