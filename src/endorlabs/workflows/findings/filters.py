"""Shared MQL list filters for finding and finding-log analytics."""

from __future__ import annotations

from datetime import datetime

MAIN_CONTEXT_CLAUSE = "context.type==CONTEXT_TYPE_MAIN"
VULNERABILITY_CATEGORY = (
    "spec.finding_categories contains FINDING_CATEGORY_VULNERABILITY"
)
REACHABLE_FUNCTION_TAGS = (
    "[FINDING_TAGS_REACHABLE_FUNCTION, FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION]"
)


def main_context_vulnerability_filter() -> str:
    """Main-context vulnerability findings filter fragment."""
    return f"{MAIN_CONTEXT_CLAUSE} and {VULNERABILITY_CATEGORY}"


def reachable_vuln_log_base_filter() -> str:
    """Base filter for reachable / PRF function vulnerability FindingLog events."""
    return (
        f"{main_context_vulnerability_filter()} "
        f"and spec.finding_tags contains {REACHABLE_FUNCTION_TAGS}"
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


def pv_main_context_filter() -> str:
    """Main-context PackageVersion list filter."""
    return MAIN_CONTEXT_CLAUSE


def _iso_z(dt: datetime) -> str:
    from datetime import UTC

    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
