"""
This module provides a resource-oriented interface for managing Endor Labs
projects. It implements CRUD operations following REST principles and
provides type-safe data models.
"""

import logging
import os
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..utils import SchemaDriftDetector

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


# Pydantic Models for Project data based on actual API response
class IndexData(BaseModel):
    """Index data for a project."""

    data: List[str]
    tenant: str


class ProjectMeta(BaseModel):
    """
    Metadata for an Endor Labs project based on actual API response.

    Attributes:
        create_time: When the project was created
        created_by: Who created the project
        index_data: Index data for the project
        kind: The kind of resource (Project)
        name: The name of the project
        update_time: When the project was last updated
        updated_by: Who last updated the project
        version: The version of the project
        description: Optional description (can be None)
    """

    create_time: str
    created_by: str
    index_data: IndexData
    kind: str
    name: str
    update_time: str
    updated_by: str
    version: str
    description: Optional[str] = None
    upsert_time: Optional[str] = None
    tags: Optional[List[str]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that the name is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("name cannot be empty")
        return v


class ProjectMetaCreate(BaseModel):
    """
    Metadata for creating an Endor Labs project.
    """

    name: str = Field(
        ..., min_length=1, max_length=255, description="The name of the project"
    )
    description: str = Field(
        ..., min_length=1, description="Description of the project's purpose"
    )
    repository_url: str = Field("", description="Repository URL for the project")
    language: str = Field("", description="Primary programming language")
    framework: str = Field("", description="Framework used in the project")


class ProjectMetaUpdate(BaseModel):
    """
    Metadata for updating an Endor Labs project.
    """

    description: Optional[str] = Field(
        None, description="Updated description of the project's purpose"
    )
    repository_url: Optional[str] = Field(
        None, description="Updated repository URL for the project"
    )
    language: Optional[str] = Field(
        None, description="Updated primary programming language"
    )
    framework: Optional[str] = Field(
        None, description="Updated framework used in the project"
    )
    tags: Optional[List[str]] = Field(None, description="Updated tags for the project")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate tags are not empty strings."""
        if v:
            return [tag.strip() for tag in v if tag.strip()]
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate description is not just whitespace."""
        if v and not v.strip():
            raise ValueError("description cannot be empty or whitespace")
        return v.strip() if v else v


class UpdateProjectPayload(BaseModel):
    """
    Payload for updating an Endor Labs project.

    MUTABLE FIELDS (can be updated via PATCH):
    - meta.description: Project description
    - meta.tags: List of tags for categorization

    IMMUTABLE FIELDS (read-only, managed by API):
    - uuid: Unique identifier (set at creation)
    - meta.name: Project name (set at creation)
    - meta.create_time, meta.created_by: Creation metadata
    - meta.update_time, meta.updated_by: Auto-managed timestamps
    - meta.repository_url: Repository URL (not API-mutable)
    - meta.language: Primary programming language (not API-mutable)
    - meta.framework: Framework used (not API-mutable)
    - spec.git.*: Git information (synced from repository)
    - tenant_meta.namespace: Namespace assignment
    - processing_status.*: Scan state (managed by scan service)

    Example:
        >>> payload = UpdateProjectPayload(
        ...     meta=ProjectMetaUpdate(
        ...         description="Backend API service",
        ...         tags=["production", "backend"]
        ...     )
        ... )
        >>> project = update_project(
        ...     client, namespace, uuid, payload, "meta.description,meta.tags"
        ... )
    """

    meta: ProjectMetaUpdate = Field(..., description="Updated metadata for the project")


class GitInfo(BaseModel):
    """Git information for a project."""

    full_name: str
    git_clone_url: str
    http_clone_url: str
    organization: str
    path: str
    web_url: str


class ProjectSpec(BaseModel):
    """Project specification."""

    git: GitInfo
    internal_reference_key: str
    platform_source: str


class ProcessingStatus(BaseModel):
    """Processing status for a project."""

    disable_automated_scan: bool
    scan_state: str
    scan_time: str


class TenantMeta(BaseModel):
    """Tenant metadata."""

    namespace: str


class Project(BaseModel):
    """
    An Endor Labs project entity based on actual API response.

    Attributes:
        meta: Project metadata
        processing_status: Processing status information
        spec: Project specification including git info
        tenant_meta: Tenant metadata including namespace
        uuid: Unique identifier for the project
    """

    meta: ProjectMeta
    processing_status: ProcessingStatus
    spec: ProjectSpec
    tenant_meta: TenantMeta
    uuid: str

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            # Define expected fields for each model
            model_fields = {
                "meta": {
                    "create_time",
                    "created_by",
                    "index_data",
                    "kind",
                    "name",
                    "update_time",
                    "updated_by",
                    "version",
                    "description",
                    "parent_uuid",
                    "parent_kind",
                    "tags",
                    "annotations",
                    "references",
                    "upsert_time",
                },
                "processing_status": {
                    "scan_state",
                    "scan_time",
                    "scan_error",
                    "scan_progress",
                    "scan_duration",
                    "last_scan_time",
                    "next_scan_time",
                    "scan_frequency",
                    "scan_enabled",
                    "analytic_time",
                    "queue_time",
                    "disable_automated_scan",
                    "metadata",
                },
                "spec": {
                    "git_info",
                    "language",
                    "framework",
                    "repository_url",
                    "branch",
                    "commit_hash",
                    "scan_config",
                    "policy_config",
                    "notification_config",
                    "integration_config",
                    "platform_source",
                    "internal_reference_key",
                    "git",
                    "ingestion_token",
                    "toolchain_profile_uuid",
                    "scan_profile_uuid",
                },
                "tenant_meta": {"namespace", "tenant_id", "tenant_name"},
            }

            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields[info.field_name], f"Project.{info.field_name}"
                )

        return v

    @field_validator("uuid")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Validate that the UUID is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("uuid cannot be empty")
        return v


class CreateProjectPayload(BaseModel):
    """
    Payload for creating a new project.

    Attributes:
        meta: Metadata for the new project
        namespace_uuid: UUID of the parent namespace
    """

    meta: ProjectMetaCreate = Field(..., description="Metadata for the new project")
    namespace_uuid: str = Field(..., description="UUID of the parent namespace")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "meta": {
                    "name": "example-project",
                    "description": "An example project",
                    "repository_url": "https://github.com/owner/repo",
                    "language": "Python",
                    "framework": "FastAPI",
                },
                "namespace_uuid": "namespace-uuid-here",
            }
        }
    )


def list_projects(client: APIClient, tenant_meta_namespace: str) -> List[Project]:
    """
    List all projects in the specified namespace.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name
            (e.g., 'endor-solutions-tgowan.cockpit')

    Returns:
        List[Project]: A list of Project objects. Empty list if error occurs.

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    try:
        headers = client.default_headers
        res = client.get(
            f"v1/namespaces/{tenant_meta_namespace}/projects", headers=headers
        )
        data = res.json()
        # Handle the actual API response structure: list.objects
        projects_data = data.get("list", {}).get("objects", [])
        return [Project(**item) for item in projects_data]
    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        return []


def get_project(
    client: APIClient, tenant_meta_namespace: str, project_uuid: str
) -> Optional[Project]:
    """
    Retrieve a specific project by UUID.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name
            (e.g., 'endor-solutions-tgowan.cockpit')
        project_uuid: The UUID of the project to retrieve

    Returns:
        Optional[Project]: The requested Project object, or None if not found

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    try:
        headers = client.default_headers
        res = client.get(
            f"v1/namespaces/{tenant_meta_namespace}/projects/{project_uuid}",
            headers=headers,
        )
        data = res.json()
        return Project(**data)
    except Exception as e:
        logger.error(f"Error retrieving project {project_uuid}: {e}", exc_info=True)
        return None


def create_project(
    client: APIClient, tenant_meta_namespace: str, payload: CreateProjectPayload
) -> Optional[Project]:
    """
    Create a new project in the specified namespace.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name
            (e.g., 'endor-solutions-tgowan.cockpit')
        payload: The CreateProjectPayload containing the new project details

    Returns:
        Optional[Project]: The created Project object, or None if creation fails

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    try:
        headers = client.default_headers
        headers.update({"Accept": "application/json"})
        res = client.post(
            f"v1/namespaces/{tenant_meta_namespace}/projects",
            headers=headers,
            data=payload.model_dump(),
        )
        data = res.json()
        return Project(**data)
    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        return None


def update_project(
    client: APIClient,
    tenant_meta_namespace: str,
    project_uuid: str,
    payload: UpdateProjectPayload,
    update_mask: Optional[str] = None,
) -> Optional[Project]:
    """
    Update an existing project using partial updates.

    This function supports updating only specific fields using the update_mask
    parameter, which enables efficient partial updates without overwriting
    unchanged fields.

    MUTABLE FIELDS:
    - meta.description: Project description
    - meta.tags: List of tags for categorization

    IMMUTABLE FIELDS (cannot be updated):
    - uuid, meta.name: Set at creation
    - meta.create_time, meta.created_by: Creation metadata
    - meta.repository_url: Repository URL (not API-mutable)
    - meta.language: Primary programming language (not API-mutable)
    - meta.framework: Framework used (not API-mutable)
    - spec.*: Git information (synced from repository)
    - tenant_meta.namespace: Namespace assignment
    - processing_status.*: Managed by scan service

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The fully qualified namespace name
            (e.g., 'endor-solutions-tgowan.cockpit')
        project_uuid: The UUID of the project to update
        payload: The UpdateProjectPayload containing the updated project details
        update_mask: Optional comma-separated list of fields to update
            (e.g., "meta.tags,meta.description"). If provided, only these
            fields will be updated. If omitted, all non-None fields in
            payload will be updated.

    Returns:
        Optional[Project]: The updated Project object with current field values,
            or None if update fails

    Raises:
        requests.exceptions.HTTPError: For API-level errors (403, 404, etc.)
        pydantic.ValidationError: If response data doesn't match expected schema
        ValueError: If attempting to update immutable fields

    Example:
        >>> # Update only tags
        >>> payload = UpdateProjectPayload(
        ...     meta=ProjectMetaUpdate(tags=["production"])
        ... )
        >>> project = update_project(client, namespace, uuid, payload, "meta.tags")

        >>> # Update multiple fields
        >>> payload = UpdateProjectPayload(
        ...     meta=ProjectMetaUpdate(
        ...         description="Backend API service",
        ...         tags=["production", "backend"],
        ...         language="python"
        ...     )
        ... )
        >>> project = update_project(
        ...     client, namespace, uuid, payload,
        ...     "meta.description,meta.tags,meta.language"
        ... )

    Note:
        Tags persist correctly when using update_mask. Without update_mask,
        the API may not persist tag changes reliably.
    """
    try:
        headers = client.default_headers
        headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

        # Get the current project to include required fields
        current_project = get_project(client, tenant_meta_namespace, project_uuid)
        if not current_project:
            logger.error(f"Project {project_uuid} not found")
            return None

        # Build request data with correct structure
        request_data = {
            "object": {
                "uuid": project_uuid,
                "tenant_meta": current_project.tenant_meta.model_dump(),
                "meta": {
                    "name": current_project.meta.name,  # Required field
                    **(
                        payload.meta.model_dump(exclude_none=True)
                        if payload.meta else {}
                    ),
                },
                "spec": current_project.spec.model_dump(),  # Required field
            }
        }

        # Add update_mask if provided for partial updates
        if update_mask:
            request_data["request"] = {"update_mask": update_mask}

        logger.info(f"Updating project {project_uuid} with mask: {update_mask}")

        res = client.patch(
            f"v1/namespaces/{tenant_meta_namespace}/projects",
            headers=headers,
            data=request_data,
        )

        if res.status_code == 200:
            data = res.json()
            return Project(**data)
        else:
            logger.error(
                f"Failed to update project {project_uuid}: "
                f"{res.status_code} - {res.text}"
            )
            return None
    except Exception as e:
        logger.error(f"Error updating project {project_uuid}: {e}", exc_info=True)
        return None


def delete_project(
    client: APIClient, tenant_meta_namespace: str, project_uuid: str
) -> bool:
    """
    Delete a project by UUID.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name
            (e.g., 'endor-solutions-tgowan.cockpit')
        project_uuid: The UUID of the project to delete

    Returns:
        bool: True if deletion was successful, False otherwise

    Raises:
        requests.exceptions.HTTPError: For API-level errors
    """
    try:
        headers = client.default_headers
        res = client.delete(
            f"v1/namespaces/{tenant_meta_namespace}/projects/{project_uuid}",
            headers=headers,
        )
        return res.status_code == 200  # Endor's API returns 200 on successful deletion
    except Exception as e:
        logger.error(f"Error deleting project {project_uuid}: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # Example usage
    client = APIClient()
    tenant_meta_namespace = os.getenv(
        "ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit"
    )

    # List projects
    print("Listing projects...")
    projects = list_projects(client, tenant_meta_namespace)
    print(f"Found {len(projects)} projects")

    for project in projects[:3]:  # Show first 3
        print(f"  - {project.meta.name} (UUID: {project.uuid})")
