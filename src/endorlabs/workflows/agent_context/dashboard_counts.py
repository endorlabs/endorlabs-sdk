"""Query-backed dashboard count helpers for agent context workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from endorlabs import Client


def project_category_counts(
    client: Client,
    projects: list[Any],
) -> dict[str, dict[str, int]]:
    """Return per-project finding category totals via Query graph join."""
    return client.Query.Project.count_findings_by_category(projects)


def project_pv_counts(
    client: Client,
    projects: list[Any],
) -> dict[str, int]:
    """Return per-project main-context PackageVersion counts via Query."""
    return client.Query.Project.count_pv(projects)
