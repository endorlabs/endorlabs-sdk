"""Repository resource module for Endor Labs API.

This module provides CRUD operations for Repository resources following the established
patterns from the base class implementation.

API OPERATIONS SUPPORTED:
- GET: List repositories, Get repository by UUID

API LIMITATIONS:
- CREATE: Not supported by API (repositories are managed by platform integrations)
- UPDATE: Not supported by API (repository metadata is read-only)
- DELETE: Not supported by API (repositories are managed by platform integrations)

Note: Repositories are auto-discovered and managed through platform integrations
(GitHub, GitLab, etc.) and cannot be manually created, updated, or deleted via API.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseResourceOperations,
    BaseSpec,
    FlexibleEnum,
)

if TYPE_CHECKING:
    from ..types import ListParameters

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


class PlatformSource(FlexibleEnum):
    """Platform source enumeration."""

    UNSPECIFIED = "PLATFORM_SOURCE_UNSPECIFIED"
    GITHUB = "PLATFORM_SOURCE_GITHUB"
    GITLAB = "PLATFORM_SOURCE_GITLAB"
    GITSERVER = "PLATFORM_SOURCE_GITSERVER"
    BITBUCKET = "PLATFORM_SOURCE_BITBUCKET"
    BINARY = "PLATFORM_SOURCE_BINARY"
    HUGGING_FACE = "PLATFORM_SOURCE_HUGGING_FACE"
    AZURE = "PLATFORM_SOURCE_AZURE"
    ARCHIVE = "PLATFORM_SOURCE_ARCHIVE"
    EXTERNAL_AI_SERVICE = "PLATFORM_SOURCE_EXTERNAL_AI_SERVICE"
    GITHUB_ENTERPRISE = "PLATFORM_SOURCE_GITHUB_ENTERPRISE"


class PlatformAccount(BaseModel):
    """Platform account information."""

    external_id: str | None = Field(
        None, description="External ID of the platform account (may be masked)"
    )
    platform_source: PlatformSource | None = Field(
        None, description="Platform source (may be masked)"
    )


class Languages(BaseModel):
    """Repository languages information."""

    languages: list[str] | None = Field(
        None, description="List of programming languages (may be masked)"
    )


class Tag(BaseModel):
    """Repository tag information."""

    name: str = Field(..., description="Tag name")
    commit_sha: str | None = Field(None, description="Commit SHA")


class BranchProtection(BaseModel):
    """Branch protection rules."""

    required_status_checks: dict[str, Any] | None = Field(
        None, description="Required status checks"
    )
    enforce_admins: bool | None = Field(None, description="Enforce admins")
    required_pull_request_reviews: dict[str, Any] | None = Field(
        None, description="Required PR reviews"
    )
    restrictions: dict[str, Any] | None = Field(None, description="Restrictions")


class Organization(BaseModel):
    """Organization information."""

    external_id: str | None = Field(
        None, description="Organization external ID (may be masked)"
    )
    name: str | None = Field(None, description="Organization name (may be masked)")
    platform_source: PlatformSource | None = Field(
        None, description="Platform source (may be masked)"
    )


class RepositoryLicense(BaseModel):
    """Repository license information."""

    key: str | None = Field(None, description="License key (may be masked)")
    name: str | None = Field(None, description="License name (may be masked)")
    spdx_id: str | None = Field(None, description="SPDX ID")
    url: str | None = Field(None, description="License URL")


class RepositoryMeta(BaseMeta):
    """Repository metadata extending BaseMeta."""

    # Repository-specific fields only (universal fields inherited from BaseMeta)
    pass


class RepositorySpec(BaseSpec):
    """Repository specification extending BaseSpec.

    Field Mutability Guide:
    ======================

    FIELD MUTABILITY (per OpenAPI spec):
    =====================================
    Note: v1RepositorySpec has NO fields marked as readOnly: true in the
    API spec. This means all RepositorySpec fields are technically mutable
    via the Update endpoint.

    However, UpdateRepository requires meta and ingested_object, and most fields are
    typically managed by platform integrations and updated through ingestion.
    """

    # Optional when list mask omits spec.platform_source or other spec fields
    platform_source: PlatformSource | None = Field(
        None,
        description="The source control platform to which the platform account belongs",
    )  # IMMUTABLE: Set at creation
    external_id: str | None = Field(
        None,
        description="Unique identifier of repo in source platform before ingestion",
    )  # IMMUTABLE: Set at creation
    http_clone_url: str | None = Field(
        None,
        description="The HTTP clone URL of the project. For example, https://github.com/yarpc/yarpc-go.git.",
    )  # IMMUTABLE: Set at creation
    owner: PlatformAccount | None = Field(
        None, description="Determines the owner of the repository"
    )  # IMMUTABLE: Set at creation
    create_time: datetime | None = Field(
        None, description="Create time of the repository in the platform"
    )  # IMMUTABLE: System-managed
    update_time: datetime | None = Field(
        None, description="Update time of the repository in the platform"
    )  # IMMUTABLE: System-managed
    contributors: list[str] | None = Field(
        None,
        description="Account external_ids seen throughout the ingestion process",
    )  # IMMUTABLE: System-managed
    commit_hashes: list[str] | None = Field(
        None,
        description="List of all commit hashes present in the repository",
    )  # IMMUTABLE: System-managed
    languages: Languages | None = Field(
        None, description="The languages of the repository"
    )  # IMMUTABLE: Analysis-determined
    tags: list[Tag] | None = Field(
        None, description="The tags of the repository"
    )  # IMMUTABLE: System-managed
    branch_protections: dict[str, Any] | None = Field(
        None,
        description="Map of branch name to GitHub branch protection rules",
    )  # IMMUTABLE: System-managed
    vulnerability_alerts_enabled: bool | None = Field(
        None,
        description="Whether vulnerability alerts are enabled on source control repo",
    )  # IMMUTABLE: System-managed
    default_branch: str | None = Field(
        None, description="The default branch of the source control repository"
    )  # IMMUTABLE: Set at creation; optional when list mask omits it
    org: Organization | None = Field(
        None,
        description="GitHub organization information available for this repository",
    )  # IMMUTABLE: Set at creation
    repository_license: RepositoryLicense | None = Field(
        None, description="The license of the repository"
    )  # IMMUTABLE: Analysis-determined

    @field_validator("platform_source", mode="before")
    @classmethod
    def validate_platform_source(cls, v: Any) -> Any:
        """Handle unknown platform source values gracefully."""
        if isinstance(v, str):
            try:
                return PlatformSource(v)
            except ValueError:
                logger.warning(f"Unknown PlatformSource value: {v}. Using as-is.")
                return v
        return v


class Repository(BaseResource):
    """Repository resource model extending BaseResource.

    OPERATION SUPPORT:
    ==================
    ✅ GET: List repositories, Get by UUID
    ❌ CREATE: Not supported (managed by platform integrations)
    ❌ UPDATE: Not supported (repository metadata is read-only)
    ❌ DELETE: Not supported (managed by platform integrations)

    FIELD MUTABILITY:
    =================
    IMMUTABLE FIELDS (read-only, system-managed):
    - uuid: Unique identifier
    - meta.name: Repository name (set by platform)
    - spec.platform_source: Platform source (set at discovery)
    - spec.http_clone_url: Clone URL (set by platform)
    - spec.external_id: External platform ID (set by platform)
    - tenant_meta.namespace: Namespace assignment
    - All spec fields: Platform-managed metadata

    Note: Repository metadata is automatically synchronized from platform integrations
    and cannot be manually modified through the API.
    """

    # Repository-specific fields (universal fields inherited from BaseResource)
    spec: RepositorySpec = Field(..., description="Repository specification")  # type: ignore
    # Conditional attributes from Resource Guide example
    ingested_object: dict[str, Any] | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Ingested object information", alias="ingested_object"
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data: Any) -> None:
        # Convert spec to RepositorySpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = RepositorySpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "create_time",
                "default_branch",
                "http_clone_url",
                "platform_source",
            }
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v


def _get_repository_ops(client: APIClient) -> BaseResourceOperations[Repository]:
    """Get BaseResourceOperations instance for Repository."""
    return BaseResourceOperations(client, "repositories", Repository)


def list_repositories(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[Repository]:
    """List repositories with advanced filtering and pagination."""
    ops = _get_repository_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def get_repository(
    client: APIClient, tenant_meta_namespace: str, repository_uuid: str
) -> Repository:
    """Get specific repository by UUID.

    Raises:
        NotFoundError: If repository doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    ops = _get_repository_ops(client)
    return ops.get(tenant_meta_namespace, repository_uuid)


def create_repository(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateRepositoryPayload,
) -> Repository:
    """Create a new repository with pre-validation and typed errors.

    Raises:
        ValidationError: If payload is invalid
        NotFoundError: If namespace doesn't exist
        PermissionDeniedError: If user lacks permission
        ConflictError: If repository already exists
        ServerError: If server error occurs

    """
    ops = _get_repository_ops(client)
    return ops.create(tenant_meta_namespace, payload)


def update_repository(
    client: APIClient,
    tenant_meta_namespace: str,
    repository_uuid: str,
    payload: UpdateRepositoryPayload,
    update_mask: str | None = None,
) -> Repository | None:
    """Update an existing repository with partial updates.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        repository_uuid: UUID of the repository to update
        payload: Repository update payload
        update_mask: Optional comma-separated list of fields to update
            (e.g., "meta.tags,meta.description"). If provided, only these
            fields will be updated. If omitted, all non-None fields in
            payload will be updated.

    Returns:
        Updated Repository object

    Raises:
        ValidationError: If payload is invalid
        NotFoundError: If repository doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    # Convert update_mask from string to List[str] for base class
    update_mask_list = (
        [field.strip() for field in update_mask.split(",")] if update_mask else None
    )
    ops = _get_repository_ops(client)
    return ops.update(tenant_meta_namespace, repository_uuid, payload, update_mask_list)


def delete_repository(
    client: APIClient, tenant_meta_namespace: str, repository_uuid: str
) -> bool:
    """Delete a repository by UUID."""
    ops = _get_repository_ops(client)
    return ops.delete(tenant_meta_namespace, repository_uuid)


# Payload models for create and update operations
class CreateRepositoryPayload(BaseModel):
    """Payload for creating a repository."""

    meta: RepositoryMetaCreate = Field(
        ..., description="Repository metadata for creation"
    )
    spec: RepositorySpec = Field(..., description="Repository specification")


class UpdateRepositoryPayload(BaseModel):
    """Payload for updating a repository."""

    meta: RepositoryMetaUpdate | None = Field(
        None, description="Repository metadata for update"
    )
    spec: RepositorySpec | None = Field(
        None, description="Repository specification for update"
    )


class RepositoryMetaCreate(BaseModel):
    """Repository metadata for creation."""

    name: str = Field(..., description="Repository name")
    description: str | None = Field(None, description="Repository description")


class RepositoryMetaUpdate(BaseModel):
    """Repository metadata for update."""

    description: str | None = Field(None, description="Repository description")
