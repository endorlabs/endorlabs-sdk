"""Compare Query recipe output to facade count baselines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .filters import FINDING_CATEGORIES, category_filter, pv_count_filter
from .recipes import count_findings_by_category, count_pv_by_project

RecipeKind = Literal["pv", "findings"]


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
        from .execute import project_namespace, project_uuid

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
    from .execute import project_namespace, project_uuid

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


def validate_sample(
    client: Any,
    projects: list[Any],
    *,
    recipe: RecipeKind = "pv",
    sample_size: int = 5,
) -> ValidationResult:
    """Compare Query recipe output to facade ``count()`` on a bounded sample."""
    sample = _sample_projects(projects, sample_size)
    mismatches: list[ValidationMismatch] = []

    if recipe == "pv":
        query_counts = count_pv_by_project(client, sample)
        facade_counts = _facade_pv_counts(client, sample)
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
    else:
        query_counts = count_findings_by_category(client, sample)
        facade_counts = _facade_finding_counts(client, sample)
        for uid in sorted(set(query_counts) | set(facade_counts)):
            q_cats = query_counts.get(uid, {})
            f_cats = facade_counts.get(uid, {})
            for label in FINDING_CATEGORIES:
                qv = q_cats.get(label, 0)
                fv = f_cats.get(label, 0)
                if qv != fv:
                    mismatches.append(
                        ValidationMismatch(
                            project_uuid=uid,
                            category=label,
                            query_value=qv,
                            facade_value=fv,
                        )
                    )

    return ValidationResult(
        recipe=recipe,
        sample_size=len(sample),
        matched=not mismatches,
        mismatches=mismatches,
    )
