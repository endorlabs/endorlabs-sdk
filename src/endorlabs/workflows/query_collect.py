"""Shared helpers for Query-backed finding row collection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from endorlabs import Client


def collect_project_findings_via_query(
    client: Client,
    projects: list[Any],
    *,
    mask: str | None = None,
    max_root_pages: int | None = None,
    prf: bool = False,
) -> list[dict[str, Any]]:
    """Collect finding rows via ``client.Query.Project`` list join specs."""
    project_query = client.Query.Project
    if prf:
        return project_query.collect_prf_findings(
            projects,
            mask=mask,
            max_root_pages=max_root_pages,
        )
    return project_query.collect_estate_findings(
        projects,
        mask=mask,
        max_root_pages=max_root_pages,
    )
