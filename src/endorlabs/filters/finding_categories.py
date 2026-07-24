"""Finding category MQL fragments and analytics filters."""

from __future__ import annotations

from datetime import datetime

from endorlabs.filters.main_context import MAIN_CONTEXT_CLAUSE, MAIN_CONTEXT_TYPE

VULNERABILITY_CATEGORY = (
    "spec.finding_categories contains FINDING_CATEGORY_VULNERABILITY"
)
REACHABLE_FUNCTION_TAGS = (
    "[FINDING_TAGS_REACHABLE_FUNCTION, FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION]"
)

FINDING_CATEGORY_SCA = "FINDING_CATEGORY_SCA"
FINDING_CATEGORY_VULNERABILITY = "FINDING_CATEGORY_VULNERABILITY"

FINDING_CATEGORIES: dict[str, str] = {
    "VULNERABILITY": FINDING_CATEGORY_VULNERABILITY,
    "SECRETS": "FINDING_CATEGORY_SECRETS",
    "MALWARE": "FINDING_CATEGORY_MALWARE",
}

CATEGORY_QUERY_REFS: dict[str, str] = {
    "VULNERABILITY": "VulnerabilityFindingsCount",
    "SECRETS": "SecretsFindingsCount",
    "MALWARE": "MalwareFindingsCount",
}

FINDING_SEVERITY_LEVELS: dict[str, str] = {
    "CRITICAL": "FINDING_LEVEL_CRITICAL",
    "HIGH": "FINDING_LEVEL_HIGH",
}

SEVERITY_QUERY_REFS: dict[str, str] = {
    "CRITICAL": "CriticalVulnerabilityFindingsCount",
    "HIGH": "HighVulnerabilityFindingsCount",
}

DEFAULT_ESTATE_FINDING_CATEGORIES: tuple[str, ...] = (
    FINDING_CATEGORY_SCA,
    FINDING_CATEGORY_VULNERABILITY,
)


def category_filter(category_enum: str) -> str:
    """MQL filter for one finding category in main context."""
    return (
        f"{MAIN_CONTEXT_CLAUSE} and spec.finding_categories contains [{category_enum}]"
    )


def severity_level_filter(level_enum: str) -> str:
    """MQL filter for main-context vulnerability findings at one severity level."""
    return f"{main_context_vulnerability_filter()} and spec.level=={level_enum}"


def main_context_vulnerability_filter() -> str:
    """Main-context vulnerability findings filter fragment."""
    return f"{MAIN_CONTEXT_CLAUSE} and {VULNERABILITY_CATEGORY}"


def reachable_vuln_log_base_filter() -> str:
    """Base filter for reachable / PRF function vulnerability FindingLog events."""
    return (
        f"{main_context_vulnerability_filter()} "
        f"and spec.finding_tags contains {REACHABLE_FUNCTION_TAGS}"
    )


def prf_vuln_filter() -> str:
    """Main-context PRF vulnerability finding filter."""
    return (
        f"{MAIN_CONTEXT_CLAUSE} and {VULNERABILITY_CATEGORY} "
        "and spec.finding_tags contains FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION"
    )


def prd_vuln_filter() -> str:
    """Main-context PRD vulnerability finding filter."""
    return (
        f"{MAIN_CONTEXT_CLAUSE} and {VULNERABILITY_CATEGORY} "
        "and spec.finding_tags contains FINDING_TAGS_POTENTIALLY_REACHABLE_DEPENDENCY"
    )


def fix_available_vuln_filter() -> str:
    """Main-context vulnerability findings tagged fix-available."""
    return (
        f"{MAIN_CONTEXT_CLAUSE} and {VULNERABILITY_CATEGORY} "
        "and spec.finding_tags contains FINDING_TAGS_FIX_AVAILABLE"
    )


def finding_log_time_window_filter(
    window_start: datetime | str,
    window_end: datetime | str,
    *,
    base_filter: str | None = None,
) -> str:
    """Combine UTC time bounds with an optional base filter clause."""
    start = window_start if isinstance(window_start, str) else _iso_z(window_start)
    end = window_end if isinstance(window_end, str) else _iso_z(window_end)
    filt = f"meta.create_time>=date({start}) and meta.create_time<date({end})"
    if base_filter:
        filt = f"{filt} and {base_filter}"
    return filt


def estate_findings_filter() -> str:
    """Main-context SCA + vulnerability finding filter for estate collect."""
    import endorlabs

    category = endorlabs.F("spec.finding_categories").contains(
        FINDING_CATEGORY_SCA
    ) | endorlabs.F("spec.finding_categories").contains(FINDING_CATEGORY_VULNERABILITY)
    return str((endorlabs.F("context.type") == MAIN_CONTEXT_TYPE) & category)


def _iso_z(dt: datetime) -> str:
    from datetime import UTC

    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
