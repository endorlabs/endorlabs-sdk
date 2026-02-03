"""RepositoryVersion resource module for Endor Labs API.

This module provides CRUD operations for RepositoryVersion resources following the
established patterns from the base class implementation.

API OPERATIONS SUPPORTED:
- GET: List repository versions, Get repository version by UUID

API LIMITATIONS:
- CREATE: Not supported (repository versions managed by platform integrations)
- UPDATE: Not supported by API (repository versions are read-only)
- DELETE: Not supported (repository versions managed by platform integrations)

Note: Repository versions are automatically discovered and managed through platform
integrations and cannot be manually created, updated, or deleted through the API.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime
from typing import TYPE_CHECKING, Any, override

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..models.base import BaseMeta, BaseResource, BaseResourceOperations, BaseSpec

if TYPE_CHECKING:
    from ..types import ListParameters

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


class RepositoryVersionMeta(BaseMeta):
    """RepositoryVersion metadata extending BaseMeta."""

    # RepositoryVersion-specific fields only (universal fields inherited from BaseMeta)
    pass


class VersionInfo(BaseModel):
    """Version information for RepositoryVersion matching v1Version spec."""

    sha: str | None = Field(
        None,
        description="SHA of source control version. Optional if SHA cannot resolve.",
    )
    ref: str | None = Field(
        None,
        description="Resolved ref of source control version: tag, branch, or SHA",
    )
    metadata: dict[str, Any] | None = Field(None, description="Version metadata.")


class RepositoryVersionSpec(BaseSpec):
    """RepositoryVersion specification extending BaseSpec.

    Field Mutability Guide:
    ======================

    FIELD MUTABILITY (per OpenAPI spec):
    =====================================
    Note: v1RepositoryVersionSpec has NO fields marked as readOnly: true
    in the API spec. This means all RepositoryVersionSpec fields are
    technically mutable via the Update endpoint.

    However, UpdateRepositoryVersion requires meta and context, and most fields are
    typically managed by platform integrations.
    """

    version: VersionInfo | None = Field(
        None, description="Version information with ref, sha, and metadata"
    )  # IMMUTABLE: Set at creation
    last_commit_date: datetime | None = Field(
        None, description="The last known time when the repository version was updated"
    )  # IMMUTABLE: System-managed


class RepositoryVersion(BaseResource):
    """RepositoryVersion resource model extending BaseResource.

    OPERATION SUPPORT:
    ==================
    ✅ GET: List repository versions, Get by UUID
    ❌ CREATE: Not supported (managed by platform integrations)
    ❌ UPDATE: Not supported (repository versions are read-only)
    ❌ DELETE: Not supported (managed by platform integrations)

    FIELD MUTABILITY (per OpenAPI spec):
    =====================================
    IMMUTABLE FIELDS (readOnly: true in API spec):
    - uuid: Unique identifier (readOnly: true in UpdateRepositoryVersion request body)
    - meta.create_time, meta.update_time, meta.upsert_time: Timestamps
      (readOnly: true in v1Meta)
    - meta.kind, meta.version: Resource metadata (readOnly: true in v1Meta)
    - meta.created_by, meta.updated_by: Audit fields (readOnly: true in v1Meta)
    - meta.references, meta.index_data: System-managed fields (readOnly: true in v1Meta)
    - tenant_meta.namespace: Namespace assignment

    MUTABLE FIELDS (NOT readOnly in API spec):
    - meta.name, meta.description, meta.tags: Metadata
    - spec.version: Version information (NOT readOnly in v1RepositoryVersionSpec)
    - spec.last_commit_date: Last commit date (NOT readOnly in v1RepositoryVersionSpec)
    - scan_object.*: Scan object fields
    - context.*: Context fields

    Note: Repository versions are automatically synchronized from platform integrations
    and typically should not be manually updated through the API.
    """

    # RepositoryVersion-specific fields (universal fields inherited from BaseResource)
    spec: RepositoryVersionSpec = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        ..., description="RepositoryVersion specification"
    )
    # Conditional attributes from Resource Guide example
    context: dict[str, Any] | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Contextual information", alias="context"
    )
    scan_object: dict[str, Any] | None = Field(
        None, description="Scan object information", alias="scan_object"
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data: Any) -> None:
        # Convert spec to RepositoryVersionSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = RepositoryVersionSpec(**data["spec"])
        super().__init__(**data)

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {"version", "last_commit_date"}
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v

    @override
    @classmethod
    def get_mutable_fields_cls(cls) -> list[str]:
        """Get list of mutable fields for RepositoryVersion."""
        return ["meta.name", "meta.description", "meta.tags", "spec"]


def _get_repository_version_ops(
    client: APIClient,
) -> BaseResourceOperations[RepositoryVersion]:
    """Get BaseResourceOperations instance for RepositoryVersion."""
    return BaseResourceOperations(client, "repository-versions", RepositoryVersion)


def list_repository_versions(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[RepositoryVersion]:
    """List repository versions with advanced filtering and pagination."""
    ops = _get_repository_version_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def list_repository_versions_iter(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[RepositoryVersion]:
    """Iterate over repository versions without materializing the full list."""
    ops = _get_repository_version_ops(client)
    return ops.list_iter(tenant_meta_namespace, list_params, max_pages, **kwargs)


def get_repository_version(
    client: APIClient, tenant_meta_namespace: str, repository_version_uuid: str
) -> RepositoryVersion:
    """Get specific repository version by UUID.

    Raises:
        NotFoundError: If repository version doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    ops = _get_repository_version_ops(client)
    return ops.get(tenant_meta_namespace, repository_version_uuid)


def create_repository_version(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateRepositoryVersionPayload,
) -> RepositoryVersion:
    """Create a new repository version with pre-validation and typed errors.

    Raises:
        ValidationError: If payload is invalid
        NotFoundError: If namespace doesn't exist
        PermissionDeniedError: If user lacks permission
        ConflictError: If repository version already exists
        ServerError: If server error occurs

    """
    ops = _get_repository_version_ops(client)
    return ops.create(tenant_meta_namespace, payload)


def update_repository_version(
    client: APIClient,
    tenant_meta_namespace: str,
    repository_version_uuid: str,
    payload: UpdateRepositoryVersionPayload,
    update_mask: str,
) -> RepositoryVersion | None:
    """Update an existing repository version with partial updates.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        repository_version_uuid: UUID of the repository version to update
        payload: RepositoryVersion update payload
        update_mask: Comma-separated list of fields to update (required), e.g.
            "meta.tags,meta.description". Missing or empty raises ValidationError.

    Returns:
        Updated RepositoryVersion object

    Raises:
        ValidationError: If payload is invalid or update_mask is missing/empty
        NotFoundError: If repository version doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    from ..exceptions import ValidationError as EndorValidationError

    if not (update_mask and update_mask.strip()):
        raise EndorValidationError(
            message=(
                "Repository version update requires an update_mask "
                "(e.g. 'meta.description', 'meta.tags')."
            ),
            operation="update",
            namespace=tenant_meta_namespace,
            resource_uuid=repository_version_uuid,
        )
    # Convert update_mask from string to List[str] for base class
    update_mask_list = [
        field.strip() for field in update_mask.split(",") if field.strip()
    ]
    ops = _get_repository_version_ops(client)
    return ops.update(
        tenant_meta_namespace, repository_version_uuid, payload, update_mask_list
    )


def delete_repository_version(
    client: APIClient, tenant_meta_namespace: str, repository_version_uuid: str
) -> bool:
    """Delete a repository version by UUID."""
    ops = _get_repository_version_ops(client)
    return ops.delete(tenant_meta_namespace, repository_version_uuid)


# Payload models for create and update operations
class CreateRepositoryVersionPayload(BaseModel):
    """Payload for creating a repository version."""

    meta: RepositoryVersionMetaCreate = Field(
        ..., description="RepositoryVersion metadata for creation"
    )
    spec: RepositoryVersionSpec = Field(
        ..., description="RepositoryVersion specification"
    )


def build_create_payload(**kwargs: Any) -> CreateRepositoryVersionPayload:
    """Build CreateRepositoryVersionPayload from kwargs (decoupled create)."""
    return CreateRepositoryVersionPayload(**kwargs)


class UpdateRepositoryVersionPayload(BaseModel):
    """Payload for updating a repository version."""

    meta: RepositoryVersionMetaUpdate | None = Field(
        None, description="RepositoryVersion metadata for update"
    )
    spec: RepositoryVersionSpec | None = Field(
        None, description="RepositoryVersion specification for update"
    )


class RepositoryVersionMetaCreate(BaseModel):
    """RepositoryVersion metadata for creation."""

    name: str = Field(..., description="RepositoryVersion name")
    description: str | None = Field(None, description="RepositoryVersion description")


class RepositoryVersionMetaUpdate(BaseModel):
    """RepositoryVersion metadata for update."""

    description: str | None = Field(None, description="RepositoryVersion description")
