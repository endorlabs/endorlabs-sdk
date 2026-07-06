"""Named Query spec builders — graph joins for dashboard and collect patterns."""

from __future__ import annotations

from endorlabs.filters import (
    CATEGORY_QUERY_REFS,
    FINDING_CATEGORIES,
    category_filter,
    estate_findings_filter,
    pv_main_context_filter,
)
from endorlabs.filters.finding_categories import (
    FINDING_SEVERITY_LEVELS,
    SEVERITY_QUERY_REFS,
    prf_vuln_filter,
    severity_level_filter,
)

from .spec import QuerySpec, Reference

MAIN_CONTEXT_FILTER = pv_main_context_filter()

PV_REFERENCE_KEY = "PackageVersion"
DM_REFERENCE_KEY = "DependencyMetadata"
FINDING_REFERENCE_KEY = "Finding"

ECOSYSTEMS = ("NUGET", "NPM", "MAVEN", "PYPI")
ECO_ENUM = {
    "NUGET": "ECOSYSTEM_NUGET",
    "NPM": "ECOSYSTEM_NPM",
    "MAVEN": "ECOSYSTEM_MAVEN",
    "PYPI": "ECOSYSTEM_PYPI",
}


def dm_count_spec() -> QuerySpec:
    """Graph join: Project -> main-context DependencyMetadata count."""
    return (
        QuerySpec.root("Project")
        .mask("uuid,meta.name")
        .leaf_scope()
        .reference(
            Reference(DM_REFERENCE_KEY)
            .connect("uuid", "spec.importer_data.project_uuid")
            .count(filter=MAIN_CONTEXT_FILTER)
        )
    )


def pv_count_spec() -> QuerySpec:
    """Graph join: Project -> main-context PackageVersion count."""
    return (
        QuerySpec.root("Project")
        .mask("uuid,meta.name")
        .leaf_scope()
        .reference(
            Reference(PV_REFERENCE_KEY)
            .connect("uuid", "spec.project_uuid")
            .count(filter=MAIN_CONTEXT_FILTER)
        )
    )


def finding_category_count_spec() -> QuerySpec:
    """Graph join: Project -> Finding counts by category (main context)."""
    spec = QuerySpec.root("Project").mask("uuid,meta.name").leaf_scope()
    for label, enum in FINDING_CATEGORIES.items():
        spec = spec.reference(
            Reference("Finding", return_as=CATEGORY_QUERY_REFS[label])
            .connect("uuid", "spec.project_uuid")
            .count(filter=category_filter(enum))
        )
    return spec


def finding_severity_count_spec() -> QuerySpec:
    """Graph join: Project -> vulnerability Finding counts by severity level."""
    spec = QuerySpec.root("Project").mask("uuid,meta.name").leaf_scope()
    for label, enum in FINDING_SEVERITY_LEVELS.items():
        spec = spec.reference(
            Reference("Finding", return_as=SEVERITY_QUERY_REFS[label])
            .connect("uuid", "spec.project_uuid")
            .count(filter=severity_level_filter(enum))
        )
    return spec


def _prf_ecosystem_filter(ecosystem_enum: str) -> str:
    return f"{prf_vuln_filter()} and spec.ecosystem=={ecosystem_enum}"


def prf_ecosystem_count_spec() -> QuerySpec:
    """Graph join: Project -> PRF vulnerability Finding counts per ecosystem."""
    spec = QuerySpec.root("Project").mask("uuid,meta.name").leaf_scope()
    for eco in ECOSYSTEMS:
        spec = spec.reference(
            Reference("Finding", return_as=f"Prf{eco}Count")
            .connect("uuid", "spec.project_uuid")
            .count(filter=_prf_ecosystem_filter(ECO_ENUM[eco]))
        )
    return spec


def estate_findings_list_spec(*, mask: str | None = None) -> QuerySpec:
    """Graph join: Project -> masked main-context SCA/vulnerability Finding list."""
    finding_mask = mask or (
        "uuid,"
        "spec.level,"
        "spec.finding_categories,"
        "spec.target_dependency_package_name,"
        "spec.target_dependency_name,"
        "spec.target_dependency_version,"
        "spec.finding_tags"
    )
    return (
        QuerySpec.root("Project")
        .mask("uuid,meta.name")
        .leaf_scope()
        .reference(
            Reference(FINDING_REFERENCE_KEY)
            .connect("uuid", "spec.project_uuid")
            .list(filter=estate_findings_filter(), mask=finding_mask)
        )
    )


def prf_findings_list_spec(*, mask: str | None = None) -> QuerySpec:
    """Graph join: Project -> masked PRF vulnerability Finding list."""
    finding_mask = mask or (
        "uuid,"
        "spec.level,"
        "spec.finding_categories,"
        "spec.target_dependency_package_name,"
        "spec.target_dependency_name,"
        "spec.target_dependency_version,"
        "spec.finding_tags,"
        "spec.ecosystem"
    )
    spec = QuerySpec.root("Project").mask("uuid,meta.name").leaf_scope()
    for eco in ECOSYSTEMS:
        spec = spec.reference(
            Reference(FINDING_REFERENCE_KEY, return_as=f"Prf{eco}Findings")
            .connect("uuid", "spec.project_uuid")
            .list(filter=_prf_ecosystem_filter(ECO_ENUM[eco]), mask=finding_mask)
        )
    return spec
