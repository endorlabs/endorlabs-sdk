"""
Project lookup utilities for maneuver scripts.

This module provides functions to find projects by various criteria,
extracting common patterns used across multiple maneuver scripts.
"""

import logging
from typing import Optional

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import project
from endor_cockpit.types import ListParameters

logger = logging.getLogger(__name__)


def find_project_by_repository_url(
    client: APIClient,
    namespace: str,
    repository_url: str,
) -> Optional[str]:
    """
    Find project UUID by repository URL.

    Attempts multiple filter strategies to locate a project by its repository
    URL, including variations of GitHub URLs and fallback to full search.

    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        repository_url: Repository URL to search for

    Returns:
        Project UUID or None if not found
    """
    try:
        # Try multiple filter approaches
        # Handle both github.com and api.github.com formats
        github_url = repository_url.replace("github.com", "api.github.com")
        filter_attempts = [
            f'spec.git.web_url=="{repository_url}"',
            f'spec.git.web_url=="{repository_url}.git"',
            f'spec.git.web_url=="{github_url}"',
            f'spec.git.web_url=="{github_url}.git"',
            f'meta.name=="{repository_url}"',
            f'meta.name=="{repository_url}.git"',
            f'spec.git.full_name=="{repository_url.split("/")[-1]}"',
        ]

        for filter_expr in filter_attempts:
            logger.info(f"Trying filter: {filter_expr}")
            list_params = ListParameters(filter=filter_expr)
            projects = project.list_projects(client, namespace, list_params)

            if projects:
                project_obj = projects[0]
                logger.info(
                    f"Found project: {project_obj.meta.name} "
                    f"(UUID: {project_obj.uuid})"
                )
                return project_obj.uuid

        # Fallback: search all projects
        logger.info(
            "No projects found with filters, searching all projects..."
        )
        all_projects = project.list_projects(client, namespace)

        for proj in all_projects:
            if repository_url in str(proj.model_dump()).lower():
                logger.info(
                    f"Found matching project: {proj.meta.name} "
                    f"(UUID: {proj.uuid})"
                )
                return proj.uuid

        logger.warning(f"No project found for repository: {repository_url}")
        return None

    except Exception as e:
        logger.error(f"Error finding project: {e}")
        return None
