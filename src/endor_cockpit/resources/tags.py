"""
This module provides tagging functionality for Endor Labs resources.
Based on the actual API structure discovered through endorctl.
"""

import logging
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from ..api_client import APIClient, RedactingFilter, redaction_pattern

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


class TagInfo(BaseModel):
    """
    Information about a tag applied to a resource.

    Attributes:
        tag: The tag name
        value: Optional tag value
        created_at: When the tag was applied
    """

    tag: str = Field(..., description="The tag name")
    value: Optional[str] = Field(None, description="Optional tag value")
    created_at: Optional[datetime] = Field(None, description="When the tag was applied")


class ResourceTags(BaseModel):
    """
    Tags associated with a resource.

    Attributes:
        resource_uuid: UUID of the resource
        resource_type: Type of resource (Project, Finding, etc.)
        tags: List of tags applied to the resource
    """

    resource_uuid: str = Field(..., description="UUID of the resource")
    resource_type: str = Field(..., description="Type of resource")
    tags: List[TagInfo] = Field(default_factory=list, description="List of tags")


def get_finding_tags(client: APIClient, finding_uuid: str) -> List[str]:
    """
    Get tags for a specific finding.

    Based on the endorctl output, findings have a 'finding_tags' field
    that contains an array of tag strings.

    Args:
        client: The APIClient instance
        finding_uuid: UUID of the finding

    Returns:
        List[str]: List of tag names
    """
    try:
        # This would need to be implemented based on the actual API
        # For now, return empty list as we don't have working API access
        logger.info(f"Getting tags for finding {finding_uuid}")
        return []
    except Exception as e:
        logger.error(f"Error getting finding tags: {e}", exc_info=True)
        return []


def add_finding_tags(client: APIClient, finding_uuid: str, tags: List[str]) -> bool:
    """
    Add tags to a finding.

    Args:
        client: The APIClient instance
        finding_uuid: UUID of the finding
        tags: List of tag names to add

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # This would need to be implemented based on the actual API
        # For now, return False as we don't have working API access
        logger.info(f"Adding tags {tags} to finding {finding_uuid}")
        return False
    except Exception as e:
        logger.error(f"Error adding finding tags: {e}", exc_info=True)
        return False


def remove_finding_tags(client: APIClient, finding_uuid: str, tags: List[str]) -> bool:
    """
    Remove tags from a finding.

    Args:
        client: The APIClient instance
        finding_uuid: UUID of the finding
        tags: List of tag names to remove

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # This would need to be implemented based on the actual API
        # For now, return False as we don't have working API access
        logger.info(f"Removing tags {tags} from finding {finding_uuid}")
        return False
    except Exception as e:
        logger.error(f"Error removing finding tags: {e}", exc_info=True)
        return False


def get_project_tags(client: APIClient, project_uuid: str) -> List[str]:
    """
    Get tags for a specific project.

    Args:
        client: The APIClient instance
        project_uuid: UUID of the project

    Returns:
        List[str]: List of tag names
    """
    try:
        # This would need to be implemented based on the actual API
        # For now, return empty list as we don't have working API access
        logger.info(f"Getting tags for project {project_uuid}")
        return []
    except Exception as e:
        logger.error(f"Error getting project tags: {e}", exc_info=True)
        return []


def add_project_tags(client: APIClient, project_uuid: str, tags: List[str]) -> bool:
    """
    Add tags to a project.

    Args:
        client: The APIClient instance
        project_uuid: UUID of the project
        tags: List of tag names to add

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # This would need to be implemented based on the actual API
        # For now, return False as we don't have working API access
        logger.info(f"Adding tags {tags} to project {project_uuid}")
        return False
    except Exception as e:
        logger.error(f"Error adding project tags: {e}", exc_info=True)
        return False


def remove_project_tags(client: APIClient, project_uuid: str, tags: List[str]) -> bool:
    """
    Remove tags from a project.

    Args:
        client: The APIClient instance
        project_uuid: UUID of the project
        tags: List of tag names to remove

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # This would need to be implemented based on the actual API
        # For now, return False as we don't have working API access
        logger.info(f"Removing tags {tags} from project {project_uuid}")
        return False
    except Exception as e:
        logger.error(f"Error removing project tags: {e}", exc_info=True)
        return False


def search_by_tags(
    client: APIClient, tags: List[str], resource_type: str = "Finding"
) -> List[str]:
    """
    Search for resources by tags.

    Args:
        client: The APIClient instance
        tags: List of tags to search for
        resource_type: Type of resource to search (Finding, Project, etc.)

    Returns:
        List[str]: List of resource UUIDs that match the tags
    """
    try:
        # This would need to be implemented based on the actual API
        # For now, return empty list as we don't have working API access
        logger.info(f"Searching for {resource_type} resources with tags {tags}")
        return []
    except Exception as e:
        logger.error(f"Error searching by tags: {e}", exc_info=True)
        return []


def list_available_tags(client: APIClient, resource_type: str = "Finding") -> List[str]:
    """
    List all available tags for a resource type.

    Args:
        client: The APIClient instance
        resource_type: Type of resource (Finding, Project, etc.)

    Returns:
        List[str]: List of available tag names
    """
    try:
        # This would need to be implemented based on the actual API
        # For now, return empty list as we don't have working API access
        logger.info(f"Listing available tags for {resource_type}")
        return []
    except Exception as e:
        logger.error(f"Error listing available tags: {e}", exc_info=True)
        return []


if __name__ == "__main__":
    # Example usage
    client = APIClient()

    # Test finding tags
    finding_uuid = "68f3eb5a0d6c66f017cf211e"  # From endorctl output
    print(f"Getting tags for finding {finding_uuid}")
    tags = get_finding_tags(client, finding_uuid)
    print(f"Found tags: {tags}")

    # Test project tags
    project_uuid = "68f3b5ddf04afdad6f14be97"  # From endorctl output
    print(f"Getting tags for project {project_uuid}")
    project_tags = get_project_tags(client, project_uuid)
    print(f"Found project tags: {project_tags}")
