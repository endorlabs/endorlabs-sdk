"""Project discovery helpers for workflows."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from endorlabs import Client

__all__ = ["duplicate_project_decision", "resolve_project_candidate"]


def duplicate_project_decision(
    matches: Sequence[Any], *, max_auto: int = 3
) -> tuple[bool, list[str], str | None]:
    """Return (proceed_with_all, warnings, error_if_too_many)."""
    n = len(matches)
    if n == 0:
        return False, [], "no_projects_matched"
    if n > max_auto:
        return (
            False,
            [],
            f"too_many_project_matches:{n}>max_auto:{max_auto}",
        )
    warnings: list[str] = []
    if n > 1:
        warnings.append(
            f"duplicate_candidates:{n}:verify_these_are_distinct_projects_before_proceeding"
        )
    return True, warnings, None


def resolve_project_candidate(
    client: Client,
    name_or_uuid: str,
    *,
    namespace: str,
    traverse: bool = True,
    warnings_out: list[str] | None = None,
    max_pages: int = 0,
    page_size: int = 100,
) -> Any:
    """Return one project by UUID (get + traverse fallback) or search_by_name."""
    from endorlabs.core.exceptions import NotFoundError as EndorNotFoundError
    from endorlabs.resources.project import is_hex_project_id

    if is_hex_project_id(name_or_uuid):
        try:
            return client.Project.get(name_or_uuid, namespace=namespace)
        except EndorNotFoundError:
            matches = client.Project.search_by_name(
                name_or_uuid,
                namespace=namespace,
                traverse=True,
                max_pages=1,
                page_size=5,
            )
            if not matches:
                raise
            if warnings_out is not None:
                warnings_out.append(
                    f"Project {name_or_uuid!r} is not in namespace {namespace!r}; "
                    "resolved the same UUID via search(traverse=True)."
                )
            return matches[0]

    matches = client.Project.search_by_name(
        name_or_uuid,
        namespace=namespace,
        traverse=traverse,
        max_pages=max_pages,
        page_size=page_size,
        warnings_out=warnings_out,
    )
    if not matches:
        raise ValueError(f"No project matched: {name_or_uuid!r}")
    if len(matches) > 1 and warnings_out is not None:
        warnings_out.append(
            f"multiple_project_matches:{len(matches)}:using_first_candidate"
        )
    return matches[0]
