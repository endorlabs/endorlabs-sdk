"""Shared utilities and result types for experimental workflows.

Provides project lookup by repository URL and base result types
used across all workflow modules.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endorlabs import Client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base result types
# ---------------------------------------------------------------------------


@dataclass
class WorkflowResult:
    """Base result type for all workflow functions.

    Attributes:
        status: Overall status (``"success"``, ``"partial"``, ``"error"``).
        message: Human-readable summary of what happened.
        errors: List of error messages encountered during execution.
    """

    status: str = "success"
    message: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return True when the workflow completed without errors."""
        return self.status == "success"


# ---------------------------------------------------------------------------
# Project lookup
# ---------------------------------------------------------------------------


def _build_url_variants(repository_url: str) -> list[str]:
    """Build filter expressions for common URL variations.

    Handles ``github.com`` vs ``api.github.com``, with/without ``.git``
    suffix, and ``meta.name`` vs ``spec.git.web_url`` fields.

    Args:
        repository_url: The repository URL to search for.

    Returns:
        Ordered list of filter expressions, most specific first.
    """
    github_url = repository_url.replace("github.com", "api.github.com")
    repo_name = repository_url.rstrip("/").split("/")[-1]

    return [
        f'meta.name=="{repository_url}"',
        f'meta.name=="{repository_url}.git"',
        f'spec.git.web_url=="{repository_url}"',
        f'spec.git.web_url=="{repository_url}.git"',
        f'spec.git.web_url=="{github_url}"',
        f'spec.git.web_url=="{github_url}.git"',
        f'spec.git.full_name=="{repo_name}"',
    ]


def find_project_by_repository_url(
    client: Client,
    namespace: str,
    repository_url: str,
) -> str | None:
    """Find a project UUID by its repository URL.

    Tries multiple filter strategies (meta.name, spec.git.web_url,
    URL variants) via the Client facade. Falls back to a full list
    scan with substring matching when filters fail.

    Args:
        client: Authenticated ``endorlabs.Client`` instance.
        namespace: Namespace to search in (canonical form).
        repository_url: Repository URL to search for
            (e.g. ``"https://github.com/org/repo"``).

    Returns:
        Project UUID string, or ``None`` if no match is found.
    """
    filter_attempts = _build_url_variants(repository_url)

    for filter_expr in filter_attempts:
        logger.debug("Trying project filter: %s", filter_expr)
        projects = client.project.list(
            namespace=namespace,
            filter=filter_expr,
            max_pages=1,
        )
        if projects:
            project_obj = projects[0]
            logger.info(
                "Found project: %s (UUID: %s)",
                project_obj.meta.name,
                project_obj.uuid,
            )
            return project_obj.uuid

    # Fallback: search all projects with substring matching
    logger.debug("No projects found with filters, searching all projects...")
    all_projects = client.project.list(namespace=namespace)

    url_lower = repository_url.lower()
    for proj in all_projects:
        if url_lower in str(proj.model_dump()).lower():
            logger.info(
                "Found matching project: %s (UUID: %s)",
                proj.meta.name,
                proj.uuid,
            )
            return proj.uuid

    logger.warning("No project found for repository: %s", repository_url)
    return None
