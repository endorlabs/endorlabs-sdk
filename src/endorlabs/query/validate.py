"""Compare Query recipe output to facade count baselines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from endorlabs.filters import (
    CATEGORY_QUERY_REFS,
    FINDING_CATEGORIES,
    category_filter,
    pv_count_filter,
)
from endorlabs.filters.finding_categories import (
    FINDING_SEVERITY_LEVELS,
    SEVERITY_QUERY_REFS,
    severity_level_filter,
)
from endorlabs.filters.project_scope import dm_importer_project_filter

from .execute import QueryExecutor
from .parse import parse_project_multi_reference_counts, parse_project_reference_counts
from .recipes import (
    DM_REFERENCE_KEY,
    PV_REFERENCE_KEY,
    dm_count_spec,
    finding_category_count_spec,
    finding_severity_count_spec,
    pv_count_spec,
)
from .row_fields import project_namespace, project_uuid
from .scope import QueryScope, scopes_from_projects

RecipeKind = Literal["pv", "findings", "dm", "severity"]


@dataclass
class ValidationMismatch:
    """One project (and optional category) where Query != facade."""

    project_uuid: str
    query_value: int
    facade_value: int
    category: str | None = None


@dataclass
class ValidationResult:
    """Outcome of a sample validation run."""

    recipe: RecipeKind
    sample_size: int
    matched: bool
    mismatches: list[ValidationMismatch] = field(
        default_factory=list[ValidationMismatch]
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize validation outcome for artifacts."""
        return {
            "recipe": self.recipe,
            "sample_size": self.sample_size,
            "matched": self.matched,
            "mismatches": [
                {
                    "project_uuid": m.project_uuid,
                    "category": m.category,
                    "query": m.query_value,
                    "facade": m.facade_value,
                }
                for m in self.mismatches
            ],
        }


def _sample_projects(projects: list[Any], sample_size: int) -> list[Any]:
    if sample_size <= 0:
        return list(projects)
    return list(projects[:sample_size])


def _facade_pv_counts(client: Any, projects: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for proj in projects:
        uid = project_uuid(proj)
        ns = project_namespace(proj)
        if not uid or not ns:
            continue
        counts[uid] = client.PackageVersion.count(
            namespace=ns,
            filter=pv_count_filter(uid),
        )
    return counts


def _facade_finding_counts(
    client: Any,
    projects: list[Any],
) -> dict[str, dict[str, int]]:
    by_project: dict[str, dict[str, int]] = {}
    for proj in projects:
        uid = project_uuid(proj)
        ns = project_namespace(proj)
        if not uid or not ns:
            continue
        counts: dict[str, int] = {}
        for label, enum in FINDING_CATEGORIES.items():
            counts[label] = client.Finding.count(
                namespace=ns,
                filter=category_filter(enum) + f' and spec.project_uuid=="{uid}"',
            )
        by_project[uid] = counts
    return by_project


def _facade_dm_counts(client: Any, projects: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for proj in projects:
        uid = project_uuid(proj)
        ns = project_namespace(proj)
        if not uid or not ns:
            continue
        counts[uid] = client.DependencyMetadata.count(
            namespace=ns,
            filter=dm_importer_project_filter(uid),
        )
    return counts


def _facade_severity_counts(
    client: Any,
    projects: list[Any],
) -> dict[str, dict[str, int]]:
    by_project: dict[str, dict[str, int]] = {}
    for proj in projects:
        uid = project_uuid(proj)
        ns = project_namespace(proj)
        if not uid or not ns:
            continue
        counts: dict[str, int] = {}
        for label, enum in FINDING_SEVERITY_LEVELS.items():
            counts[label] = client.Finding.count(
                namespace=ns,
                filter=severity_level_filter(enum) + f' and spec.project_uuid=="{uid}"',
            )
        by_project[uid] = counts
    return by_project


def _count_mismatches(
    query_counts: dict[str, int],
    facade_counts: dict[str, int],
) -> list[ValidationMismatch]:
    mismatches: list[ValidationMismatch] = []
    for uid in sorted(set(query_counts) | set(facade_counts)):
        qv = query_counts.get(uid, 0)
        fv = facade_counts.get(uid, 0)
        if qv != fv:
            mismatches.append(
                ValidationMismatch(
                    project_uuid=uid,
                    query_value=qv,
                    facade_value=fv,
                )
            )
    return mismatches


def _nested_count_mismatches(
    query_counts: dict[str, dict[str, int]],
    facade_counts: dict[str, dict[str, int]],
    labels: dict[str, str],
) -> list[ValidationMismatch]:
    mismatches: list[ValidationMismatch] = []
    for uid in sorted(set(query_counts) | set(facade_counts)):
        q_map = query_counts.get(uid, {})
        f_map = facade_counts.get(uid, {})
        for label in labels:
            qv = q_map.get(label, 0)
            fv = f_map.get(label, 0)
            if qv != fv:
                mismatches.append(
                    ValidationMismatch(
                        project_uuid=uid,
                        category=label,
                        query_value=qv,
                        facade_value=fv,
                    )
                )
    return mismatches


def _parse_multi_ref_counts(
    result: Any,
    ref_keys: list[str],
    label_by_ref: dict[str, str],
) -> dict[str, dict[str, int]]:
    raw = parse_project_multi_reference_counts(result, ref_keys)
    return {
        pid: {label_by_ref[key]: count for key, count in counts.items()}
        for pid, counts in raw.items()
    }


def _validate_pv(
    client: Any,
    executor: QueryExecutor,
    scopes: list[QueryScope],
    sample: list[Any],
) -> list[ValidationMismatch]:
    query_counts = executor.execute(
        pv_count_spec(),
        scopes=scopes,
        parse_page=lambda result: parse_project_reference_counts(
            result, PV_REFERENCE_KEY
        ),
    )
    return _count_mismatches(query_counts, _facade_pv_counts(client, sample))


def _validate_dm(
    client: Any,
    executor: QueryExecutor,
    scopes: list[QueryScope],
    sample: list[Any],
) -> list[ValidationMismatch]:
    query_counts = executor.execute(
        dm_count_spec(),
        scopes=scopes,
        parse_page=lambda result: parse_project_reference_counts(
            result, DM_REFERENCE_KEY
        ),
    )
    return _count_mismatches(query_counts, _facade_dm_counts(client, sample))


def _validate_findings(
    client: Any,
    executor: QueryExecutor,
    scopes: list[QueryScope],
    sample: list[Any],
) -> list[ValidationMismatch]:
    ref_keys = list(CATEGORY_QUERY_REFS.values())
    label_by_ref = {value: key for key, value in CATEGORY_QUERY_REFS.items()}
    query_counts = executor.execute(
        finding_category_count_spec(),
        scopes=scopes,
        parse_page=lambda result: _parse_multi_ref_counts(
            result, ref_keys, label_by_ref
        ),
    )
    return _nested_count_mismatches(
        query_counts,
        _facade_finding_counts(client, sample),
        FINDING_CATEGORIES,
    )


def _validate_severity(
    client: Any,
    executor: QueryExecutor,
    scopes: list[QueryScope],
    sample: list[Any],
) -> list[ValidationMismatch]:
    ref_keys = list(SEVERITY_QUERY_REFS.values())
    label_by_ref = {value: key for key, value in SEVERITY_QUERY_REFS.items()}
    query_counts = executor.execute(
        finding_severity_count_spec(),
        scopes=scopes,
        parse_page=lambda result: _parse_multi_ref_counts(
            result, ref_keys, label_by_ref
        ),
    )
    return _nested_count_mismatches(
        query_counts,
        _facade_severity_counts(client, sample),
        FINDING_SEVERITY_LEVELS,
    )


_RECIPE_VALIDATORS = {
    "pv": _validate_pv,
    "dm": _validate_dm,
    "findings": _validate_findings,
    "severity": _validate_severity,
}


def validate_sample(
    client: Any,
    projects: list[Any],
    *,
    recipe: RecipeKind = "pv",
    sample_size: int = 5,
) -> ValidationResult:
    """Compare Query recipe output to facade ``count()`` on a bounded sample."""
    sample = _sample_projects(projects, sample_size)
    executor = QueryExecutor(client, name_prefix="query-validate")
    scopes = scopes_from_projects(sample)
    validator = _RECIPE_VALIDATORS.get(recipe)
    if validator is None:
        raise ValueError(f"unsupported validate_sample recipe: {recipe!r}")
    mismatches = validator(client, executor, scopes, sample)
    return ValidationResult(
        recipe=recipe,
        sample_size=len(sample),
        matched=not mismatches,
        mismatches=mismatches,
    )
