"""Shared MQL filter fragments for Query graph joins."""

from __future__ import annotations

from endorlabs.workflows.findings.filters import pv_main_context_filter

MAIN_CONTEXT_FILTER = pv_main_context_filter()

FINDING_CATEGORIES: dict[str, str] = {
    "VULNERABILITY": "FINDING_CATEGORY_VULNERABILITY",
    "SECRETS": "FINDING_CATEGORY_SECRETS",
    "MALWARE": "FINDING_CATEGORY_MALWARE",
}

CATEGORY_QUERY_REFS: dict[str, str] = {
    "VULNERABILITY": "VulnerabilityFindingsCount",
    "SECRETS": "SecretsFindingsCount",
    "MALWARE": "MalwareFindingsCount",
}


def category_filter(category_enum: str) -> str:
    """MQL filter for one finding category in main context."""
    return (
        f"{MAIN_CONTEXT_FILTER} and spec.finding_categories contains [{category_enum}]"
    )


def project_uuid_in_filter(uuids: list[str]) -> str:
    """MQL filter restricting a Project query to known UUIDs."""
    if not uuids:
        return ""
    inner = ", ".join(f'"{u}"' for u in uuids)
    return f"uuid in [{inner}]"


def pv_count_filter(project_uuid: str) -> str:
    """Facade-equivalent filter for one project's main-context PackageVersions."""
    return f'{MAIN_CONTEXT_FILTER} and spec.project_uuid=="{project_uuid}"'
