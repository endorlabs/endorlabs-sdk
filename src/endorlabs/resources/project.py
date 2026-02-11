"""Resource-oriented interface for managing Endor Labs projects.

Implements CRUD operations following REST principles and
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

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.base import BaseMeta, BaseResource, BaseSpec
from ..operations import BaseResourceOperations
from ..utils.logging_config import get_resource_logger

if TYPE_CHECKING:
    from ..api_client import APIClient

logger = get_resource_logger(__name__)


# Pydantic Models for Project data based on actual API response
class IndexData(BaseModel):
    """Index data for a project."""

    data: list[str]
    tenant: str


class ProjectMeta(BaseMeta):
    """Metadata for an Endor Labs project extending BaseMeta.

    Project-specific fields only (universal fields inherited from BaseMeta).
    """

    # Project-specific fields (universal fields inherited from BaseMeta)
    # Optional when list mask omits meta.index_data.
    index_data: IndexData | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Index data for the project", alias="index_data"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that the name is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("name cannot be empty")
        return v


class ProjectMetaCreate(BaseModel):
    """Metadata for creating an Endor Labs project."""

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
    """Metadata for updating an Endor Labs project."""

    description: str | None = Field(
        None, description="Updated description of the project's purpose"
    )
    repository_url: str | None = Field(
        None, description="Updated repository URL for the project"
    )
    language: str | None = Field(
        None, description="Updated primary programming language"
    )
    framework: str | None = Field(
        None, description="Updated framework used in the project"
    )
    tags: list[str] | None = Field(None, description="Updated tags for the project")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """Validate tags are not empty strings."""
        if v:
            return [tag.strip() for tag in v if tag.strip()]
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Validate description is not just whitespace."""
        if v and not v.strip():
            raise ValueError("description cannot be empty or whitespace")
        return v.strip() if v else v


class UpdateProjectPayload(BaseModel):
    """Payload for updating an Endor Labs project.

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

    full_name: str | None = None
    git_clone_url: str | None = None
    http_clone_url: str | None = None
    organization: str | None = None
    path: str | None = None
    web_url: str | None = None
    external_installation_id: str | None = Field(
        None,
        description=(
            "Endor Labs GitHub app installation ID of this project. "
            "Optional and only available if the project is created "
            "through an installation."
        ),
    )
    invalid_installation: bool | None = Field(
        None,
        description="Indicates that Endor Labs installation no longer exists "
        "for this project and was potentially deleted. Endor Labs can no longer "
        "refresh or rescan this project.",
    )


class ProjectSpec(BaseSpec):
    """Project specification extending BaseSpec."""

    git: GitInfo | None = Field(None, description="Git information for the project")
    # Optional when list mask omits spec.internal_reference_key
    internal_reference_key: str | None = Field(
        None, description="Internal reference key"
    )
    # Required per v1ProjectSpec; optional when list mask omits it
    platform_source: str | None = Field(None, description="Platform source identifier")
    scan_profile_uuid: str | None = Field(
        None, description="Scan profile UUID (mutable via PATCH)."
    )
    toolchain_profile_uuid: str | None = Field(
        None, description="Toolchain profile UUID (mutable via PATCH)."
    )
    ingestion_token: str | None = Field(
        None, description="Ingestion token (read-only)."
    )
    is_archived: bool | None = Field(
        None, description="Whether the project is archived (read-only)."
    )


class ProcessingStatus(BaseModel):
    """Processing status for a project."""

    disable_automated_scan: bool
    scan_state: str
    scan_time: str | None = None


class TenantMeta(BaseModel):
    """Tenant metadata."""

    namespace: str


class Project(BaseResource):
    """An Endor Labs project entity extending BaseResource.

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
    # Optional when list mask omits processing_status
    processing_status: ProcessingStatus | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None,
        description="Processing status information",
        alias="processing_status",
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data: Any) -> None:
        # Convert spec to ProjectSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = ProjectSpec(**data["spec"])
        super().__init__(**data)

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
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
                "is_archived",
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

    @override
    @classmethod
    def get_mutable_fields_cls(cls) -> list[str]:
        """Get list of mutable fields for Project (meta and processing_status)."""
        return [
            "meta.description",
            "meta.tags",
            "processing_status.scan_state",
            "processing_status.disable_automated_scan",
        ]

    @override
    @classmethod
    def get_immutable_fields_cls(cls) -> list[str]:
        """Get list of immutable fields for Project."""
        return [
            "uuid",
            "meta.name",
            "meta.create_time",
            "meta.created_by",
            "meta.update_time",
            "meta.updated_by",
            "spec.git",
            "tenant_meta.namespace",
        ]


class CreateProjectPayload(BaseModel):
    """Payload for creating a new project.

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


def build_create_payload(
    *,
    name: str,
    description: str,
    namespace_uuid: str,
    repository_url: str = "",
    language: str = "",
    framework: str = "",
) -> CreateProjectPayload:
    """Build CreateProjectPayload from kwargs (decoupled facade create)."""
    meta = ProjectMetaCreate(
        name=name,
        description=description,
        repository_url=repository_url,
        language=language,
        framework=framework,
    )
    return CreateProjectPayload(meta=meta, namespace_uuid=namespace_uuid)


def associate_scan_profile_with_project(
    client: APIClient,
    tenant_meta_namespace: str,
    project_uuid: str,
    scan_profile_uuid: str,
) -> Project:
    """Associate a scan profile with a project.

    This is a convenience function that updates the project's scan_profile_uuid
    field. The scan profile must exist in the same namespace.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name
            (e.g., 'tenant.namespace')
        project_uuid: The UUID of the project to update
        scan_profile_uuid: The UUID of the scan profile to associate

    Returns:
        Project: The updated Project object

    Raises:
        NotFoundError: If project or scan profile doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    Example:
        >>> project = associate_scan_profile_with_project(
        ...     client, namespace, project_uuid, scan_profile_uuid
        ... )

    """
    ops = BaseResourceOperations(client, "projects", Project)
    current_project = ops.get(tenant_meta_namespace, project_uuid)

    # Update the spec with the new scan_profile_uuid
    spec_dict = current_project.spec.model_dump()
    spec_dict["scan_profile_uuid"] = scan_profile_uuid

    # Build update payload
    tenant_meta_dict = (
        current_project.tenant_meta.model_dump()
        if current_project.tenant_meta
        else {"namespace": tenant_meta_namespace}
    )
    request_data = {
        "object": {
            "uuid": project_uuid,
            "tenant_meta": tenant_meta_dict,
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
        _ = (
            res.raise_for_status()
        )  # Will raise HTTPStatusError for non-2xx status codes
        data = res.json()
        updated_project = Project(**data)
        logger.info(
            f"Associated scan profile {scan_profile_uuid} with project {project_uuid}"
        )
        return updated_project
    except httpx.HTTPStatusError as e:
        # Map HTTP errors to typed exceptions
        raise client.map_http_error_to_exception(
            e, "update", tenant_meta_namespace, resource_uuid=project_uuid
        ) from e
    except Exception as e:
        # Unexpected errors
        from ..exceptions import ServerError

        raise ServerError(
            message=(f"Unexpected error associating scan profile with project: {e!s}"),
            operation="update",
            namespace=tenant_meta_namespace,
            resource_uuid=project_uuid,
        ) from e


def verify_scan_profile_association(
    client: APIClient,
    tenant_meta_namespace: str,
    project_uuid: str,
    scan_profile_uuid: str,
) -> bool:
    """Verify that a scan profile is associated with a project.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The canonical namespace name
        project_uuid: The UUID of the project to check
        scan_profile_uuid: The UUID of the scan profile to verify

    Returns:
        bool: True if the scan profile is associated, False otherwise

    """
    try:
        ops = BaseResourceOperations(client, "projects", Project)
        project = ops.get(tenant_meta_namespace, project_uuid)
    except Exception:
        # Project not found or other error
        return False

    current_scan_profile_uuid = getattr(project.spec, "scan_profile_uuid", None)
    is_associated = current_scan_profile_uuid == scan_profile_uuid

    if is_associated:
        logger.info(
            f"Verified: Scan profile {scan_profile_uuid} is associated "
            f"with project {project_uuid}"
        )
    else:
        logger.warning(
            f"Scan profile mismatch: Project {project_uuid} has "
            f"scan_profile_uuid={current_scan_profile_uuid}, expected "
            f"{scan_profile_uuid}"
        )

    return is_associated
