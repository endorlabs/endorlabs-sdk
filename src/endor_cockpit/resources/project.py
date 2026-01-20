"""
This module provides a resource-oriented interface for managing Endor Labs
projects. It implements CRUD operations following REST principles and
provides type-safe data models.

API OPERATIONS SUPPORTED:
- GET: List projects, Get project by UUID
- PATCH: Update project metadata and tags

API LIMITATIONS:
- CREATE: Not supported by API (projects are managed by platform integrations)
- DELETE: Not supported by API (projects are managed by platform integrations)

Note: Projects are automatically discovered and managed through platform integrations
and cannot be manually created or deleted. Only metadata updates (tags, descriptions)
are allowed via PATCH operations.
"""

import logging
import os
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..models.base import BaseMeta, BaseResource, BaseResourceOperations, BaseSpec
from ..types import ListParameters

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


# Pydantic Models for Project data based on actual API response
class IndexData(BaseModel):
    """Index data for a project."""

    data: List[str]
    tenant: str


class ProjectMeta(BaseMeta):
    """
    Metadata for an Endor Labs project extending BaseMeta.

    Project-specific fields only (universal fields inherited from BaseMeta).
    """

    # Project-specific fields (universal fields inherited from BaseMeta)
    project_index_data: IndexData = Field(
        ..., description="Index data for the project", alias="index_data"
    )

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
    - meta.name: Project name (NOT readOnly in API spec)
    - meta.description: Project description (NOT readOnly in API spec)
    - meta.tags: List of tags for categorization (NOT readOnly in API spec)
    - meta.parent_uuid, meta.parent_kind: Parent object references
      (NOT readOnly in API spec)
    - meta.annotations: Resource annotations (NOT readOnly in API spec)
    - spec.platform_source: Platform source (NOT readOnly in API spec)
    - spec.git.http_clone_url: HTTP clone URL (NOT readOnly in API spec)
    - spec.git.external_installation_id: External installation ID
      (NOT readOnly in API spec)
    - spec.git.invalid_installation: Invalid installation flag
      (NOT readOnly in API spec)
    - spec.toolchain_profile_uuid: Toolchain profile UUID (NOT readOnly in API spec)
    - spec.scan_profile_uuid: Scan profile UUID (NOT readOnly in API spec)
    - processing_status.scan_state: Scan state
      (e.g., SCAN_STATE_IDLE, SCAN_STATE_INGESTING) (NOT readOnly in API spec)
    - processing_status.disable_automated_scan: Disable automated scanning flag
      (NOT readOnly in API spec)
    - processing_status.scan_time: Last scan time
      (NOT readOnly in API spec, but typically system-managed)
    - processing_status.analytic_time: Last analytics time
      (NOT readOnly in API spec, but typically system-managed)
    - processing_status.queue_time: Last queue time
      (NOT readOnly in API spec, but typically system-managed)

    IMMUTABLE FIELDS (read-only, managed by API):
    - uuid: Unique identifier (readOnly: true in API spec)
    - meta.create_time, meta.update_time, meta.upsert_time: Timestamps
      (readOnly: true in API spec)
    - meta.kind, meta.version: Resource metadata (readOnly: true in API spec)
    - meta.created_by, meta.updated_by: Audit fields (readOnly: true in API spec)
    - meta.references, meta.index_data: System-managed fields
      (readOnly: true in API spec)
    - spec.internal_reference_key: Internal reference key (readOnly: true in API spec)
    - spec.ingestion_token: Ingestion token (readOnly: true in API spec)
    - spec.git.git_clone_url, spec.git.organization, spec.git.path,
      spec.git.full_name, spec.git.web_url: Git metadata
      (readOnly: true in API spec)
    - tenant_meta.namespace: Namespace assignment

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
    external_installation_id: Optional[str] = Field(
        None,
        description=(
            "Endor Labs GitHub app installation ID of this project. "
            "Optional and only available if the project is created "
            "through an installation."
        ),
    )
    invalid_installation: Optional[bool] = Field(
        None,
        description="Indicates that Endor Labs installation no longer exists "
        "for this project and was potentially deleted. Endor Labs can no longer "
        "refresh or rescan this project.",
    )


class ProjectSpec(BaseSpec):
    """Project specification extending BaseSpec."""

    git: GitInfo = Field(..., description="Git information for the project")
    internal_reference_key: str = Field(..., description="Internal reference key")
    platform_source: str = Field(..., description="Platform source identifier")


class ProcessingStatus(BaseModel):
    """Processing status for a project."""

    disable_automated_scan: bool
    scan_state: str
    scan_time: Optional[str] = None


class TenantMeta(BaseModel):
    """Tenant metadata."""

    namespace: str


class Project(BaseResource):
    """
    An Endor Labs project entity extending BaseResource.

    Project-specific fields (universal fields inherited from BaseResource).

    OPERATION SUPPORT:
    ==================
    ✅ GET: List projects, Get by UUID
    ✅ PATCH: Update project metadata and tags
    ❌ CREATE: Not supported (managed by platform integrations)
    ❌ DELETE: Not supported (managed by platform integrations)

    FIELD MUTABILITY (per OpenAPI spec):
    =====================================
    IMMUTABLE FIELDS (readOnly: true in API spec):
    - uuid: Unique identifier
    - meta.create_time, meta.update_time, meta.upsert_time: Timestamps
    - meta.kind, meta.version: Resource metadata
    - meta.created_by, meta.updated_by: Audit fields
    - meta.references, meta.index_data: System-managed fields
    - spec.internal_reference_key: Internal reference key
    - spec.ingestion_token: Ingestion token
    - spec.git.git_clone_url, spec.git.organization, spec.git.path,
      spec.git.full_name, spec.git.web_url: Git metadata
    - tenant_meta.namespace: Namespace assignment

    MUTABLE FIELDS (NOT readOnly in API spec):
    - meta.name: Project name
    - meta.description: Project description
    - meta.tags: Project tags
    - meta.parent_uuid, meta.parent_kind: Parent object references
    - meta.annotations: Resource annotations
    - spec.platform_source: Platform source
    - spec.git.http_clone_url: HTTP clone URL
    - spec.git.external_installation_id: External installation ID
    - spec.git.invalid_installation: Invalid installation flag
    - spec.toolchain_profile_uuid: Toolchain profile UUID
    - spec.scan_profile_uuid: Scan profile UUID
    - processing_status.*: All processing status fields
      (scan_state, disable_automated_scan, scan_time, analytic_time, queue_time)

    Note: Projects are automatically discovered through platform integrations
    and cannot be manually created or deleted. Only metadata updates are allowed.
    """

    # Project-specific fields (universal fields inherited from BaseResource)
    spec: ProjectSpec = Field(..., description="Project specification")  # type: ignore
    project_processing_status: ProcessingStatus = Field(
        ..., description="Processing status information", alias="processing_status"
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data):
        # Convert spec to ProjectSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = ProjectSpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "git",
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
                "ingestion_token",
                "toolchain_profile_uuid",
                "scan_profile_uuid",
            }
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
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


def _get_project_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for projects."""
    return BaseResourceOperations(client, "projects", Project)


def list_projects(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
) -> List[Project]:
    """
    List all projects in the specified namespace.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name
            (e.g., 'tenant.namespace')
        list_params: Optional list parameters for filtering, pagination, etc.

    Returns:
        List[Project]: A list of Project objects. Empty list if error occurs.

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    ops = _get_project_ops(client)
    results = ops.list(tenant_meta_namespace, list_params)
    return [Project(**item.model_dump()) for item in results]  # type: ignore


def get_project(
    client: APIClient, tenant_meta_namespace: str, project_uuid: str
) -> Optional[Project]:
    """
    Retrieve a specific project by UUID.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name
            (e.g., 'tenant.namespace')
        project_uuid: The UUID of the project to retrieve

    Returns:
        Optional[Project]: The requested Project object, or None if not found

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    ops = _get_project_ops(client)
    result = ops.get(tenant_meta_namespace, project_uuid)
    if result:
        return Project(**result.model_dump())  # type: ignore
    return None


def create_project(
    client: APIClient, tenant_meta_namespace: str, payload: CreateProjectPayload
) -> Optional[Project]:
    """
    Create a new project in the specified namespace.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name
            (e.g., 'tenant.namespace')
        payload: The CreateProjectPayload containing the new project details

    Returns:
        Optional[Project]: The created Project object, or None if creation fails

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    try:
        res = client.post(
            f"v1/namespaces/{tenant_meta_namespace}/projects",
            json=payload.model_dump(),
            headers={"Accept": "application/json"},
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

    FIELD MUTABILITY (per OpenAPI spec):
    =====================================
    IMMUTABLE FIELDS (readOnly: true in API spec):
    - uuid: Unique identifier
    - meta.create_time, meta.update_time, meta.upsert_time: Timestamps
    - meta.kind, meta.version: Resource metadata
    - meta.created_by, meta.updated_by: Audit fields
    - meta.references, meta.index_data: System-managed fields
    - spec.internal_reference_key: Internal reference key
    - spec.ingestion_token: Ingestion token
    - spec.git.git_clone_url, spec.git.organization, spec.git.path,
      spec.git.full_name, spec.git.web_url: Git metadata

    MUTABLE FIELDS (NOT readOnly in API spec):
    - meta.name, meta.description, meta.tags: Metadata
    - meta.parent_uuid, meta.parent_kind, meta.annotations: Additional metadata
    - spec.platform_source: Platform source
    - spec.git.http_clone_url, spec.git.external_installation_id,
      spec.git.invalid_installation: Git configuration
    - spec.toolchain_profile_uuid, spec.scan_profile_uuid: Profile references
    - processing_status.*: All processing status fields

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The fully qualified namespace name
            (e.g., 'tenant.namespace')
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
                        if payload.meta
                        else {}
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
            json=request_data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
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


def associate_scan_profile_with_project(
    client: APIClient,
    tenant_meta_namespace: str,
    project_uuid: str,
    scan_profile_uuid: str,
) -> Optional[Project]:
    """
    Associate a scan profile with a project.

    This is a convenience function that updates the project's scan_profile_uuid
    field. The scan profile must exist in the same namespace.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name
            (e.g., 'tenant.namespace')
        project_uuid: The UUID of the project to update
        scan_profile_uuid: The UUID of the scan profile to associate

    Returns:
        Optional[Project]: The updated Project object, or None if update fails

    Raises:
        requests.exceptions.HTTPError: For API-level errors (403, 404, etc.)
        pydantic.ValidationError: If response data doesn't match expected schema

    Example:
        >>> project = associate_scan_profile_with_project(
        ...     client, namespace, project_uuid, scan_profile_uuid
        ... )
    """
    # Get current project to preserve all fields
    current_project = get_project(client, tenant_meta_namespace, project_uuid)
    if not current_project:
        logger.error(f"Project {project_uuid} not found")
        return None

    # Update the spec with the new scan_profile_uuid
    spec_dict = current_project.spec.model_dump()
    spec_dict["scan_profile_uuid"] = scan_profile_uuid

    # Build update payload
    request_data = {
        "object": {
            "uuid": project_uuid,
            "tenant_meta": current_project.tenant_meta.model_dump(),
            "meta": {
                "name": current_project.meta.name,
            },
            "spec": spec_dict,
        },
        "request": {"update_mask": "spec.scan_profile_uuid"},
    }

    try:
        res = client.patch(
            f"v1/namespaces/{tenant_meta_namespace}/projects",
            json=request_data,
            headers={"Accept": "application/json"},
        )
        if res.status_code == 200:
            data = res.json()
            updated_project = Project(**data)
            logger.info(
                f"✅ Associated scan profile {scan_profile_uuid} with project "
                f"{project_uuid}"
            )
            return updated_project
        else:
            logger.error(
                f"Failed to associate scan profile: {res.status_code} - {res.text}"
            )
            return None
    except Exception as e:
        logger.error(f"Error associating scan profile: {e}", exc_info=True)
        return None


def verify_scan_profile_association(
    client: APIClient,
    tenant_meta_namespace: str,
    project_uuid: str,
    scan_profile_uuid: str,
) -> bool:
    """
    Verify that a scan profile is associated with a project.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name
        project_uuid: The UUID of the project to check
        scan_profile_uuid: The UUID of the scan profile to verify

    Returns:
        bool: True if the scan profile is associated, False otherwise
    """
    project = get_project(client, tenant_meta_namespace, project_uuid)
    if not project:
        logger.warning(f"Project {project_uuid} not found")
        return False

    current_scan_profile_uuid = getattr(project.spec, "scan_profile_uuid", None)
    is_associated = current_scan_profile_uuid == scan_profile_uuid

    if is_associated:
        logger.info(
            f"✅ Verified: Scan profile {scan_profile_uuid} is associated "
            f"with project {project_uuid}"
        )
    else:
        logger.warning(
            f"⚠️ Scan profile mismatch: Project {project_uuid} has "
            f"scan_profile_uuid={current_scan_profile_uuid}, expected "
            f"{scan_profile_uuid}"
        )

    return is_associated


def delete_project(
    client: APIClient, tenant_meta_namespace: str, project_uuid: str
) -> bool:
    """
    Delete a project by UUID.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name
            (e.g., 'tenant.namespace')
        project_uuid: The UUID of the project to delete

    Returns:
        bool: True if deletion was successful, False otherwise

    Raises:
        requests.exceptions.HTTPError: For API-level errors
    """
    try:
        res = client.delete(
            f"v1/namespaces/{tenant_meta_namespace}/projects/{project_uuid}"
        )
        return res.status_code == 200  # Endor's API returns 200 on successful deletion
    except Exception as e:
        logger.error(f"Error deleting project {project_uuid}: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # Example usage
    client = APIClient()
    tenant_meta_namespace = os.getenv("ENDOR_NAMESPACE", "")

    # List projects
    print("Listing projects...")
    projects = list_projects(client, tenant_meta_namespace)
    print(f"Found {len(projects)} projects")

    for project in projects[:3]:  # Show first 3
        print(f"  - {project.meta.name} (UUID: {project.uuid})")
