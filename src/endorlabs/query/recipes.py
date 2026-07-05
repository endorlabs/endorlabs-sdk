"""Named Query recipes for common dashboard count joins."""

from __future__ import annotations

from typing import Any

from .execute import QueryExecutor
from .filters import (
    CATEGORY_QUERY_REFS,
    FINDING_CATEGORIES,
    MAIN_CONTEXT_FILTER,
    category_filter,
)
from .parse import parse_project_multi_reference_counts, parse_project_reference_counts
from .spec import QuerySpec, Reference

PV_REFERENCE_KEY = "PackageVersion"


def pv_count_spec() -> QuerySpec:
    """Graph join: Project -> main-context PackageVersion count."""
    return (
        QuerySpec.root("Project")
        .mask("uuid,meta.name")
        .reference(
            Reference(PV_REFERENCE_KEY)
            .connect("uuid", "spec.project_uuid")
            .count(filter=MAIN_CONTEXT_FILTER)
        )
    )


def finding_category_count_spec() -> QuerySpec:
    """Graph join: Project -> Finding counts by category (main context)."""
    spec = QuerySpec.root("Project").mask("uuid,meta.name")
    for label, enum in FINDING_CATEGORIES.items():
        spec = spec.reference(
            Reference("Finding", return_as=CATEGORY_QUERY_REFS[label])
            .connect("uuid", "spec.project_uuid")
            .count(filter=category_filter(enum))
        )
    return spec


def count_pv_by_project(
    client: Any,
    projects: list[Any],
    *,
    name_prefix: str = "query-pv-counts",
) -> dict[str, int]:
    """Return ``{project_uuid: main_context_pv_count}`` via Query graph join."""
    return QueryExecutor(client, name_prefix=name_prefix).run(
        pv_count_spec(),
        projects=projects,
        parse_result=lambda result: parse_project_reference_counts(
            result, PV_REFERENCE_KEY
        ),
    )


def count_findings_by_category(
    client: Any,
    projects: list[Any],
    *,
    name_prefix: str = "query-finding-counts",
) -> dict[str, dict[str, int]]:
    """Return ``{project_uuid: {category_label: count}}`` via Query graph join."""
    ref_keys = list(CATEGORY_QUERY_REFS.values())
    label_by_ref = {value: key for key, value in CATEGORY_QUERY_REFS.items()}

    def _parse(result: Any) -> dict[str, dict[str, int]]:
        raw = parse_project_multi_reference_counts(result, ref_keys)
        return {
            pid: {label_by_ref[key]: count for key, count in counts.items()}
            for pid, counts in raw.items()
        }

    return QueryExecutor(client, name_prefix=name_prefix).run(
        finding_category_count_spec(),
        projects=projects,
        parse_result=_parse,
    )
