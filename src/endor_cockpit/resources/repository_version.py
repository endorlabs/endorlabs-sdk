"""
RepositoryVersion resource module for Endor Labs API.

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

import logging
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..models.base import BaseMeta, BaseResource, BaseResourceOperations, BaseSpec
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

    sha: Optional[str] = Field(
        None,
        description="SHA of source control version. Optional if SHA cannot resolve.",
    )
    ref: Optional[str] = Field(
        None,
        description="Resolved ref of source control version: tag, branch, or SHA",
    )
    metadata: Optional[dict] = Field(None, description="Version metadata.")


class RepositoryVersionSpec(BaseSpec):
    """RepositoryVersion specification extending BaseSpec.

    Field Mutability Guide:
    ======================

    IMMUTABLE FIELDS (cannot be updated after creation):
    - version: Version information (set at creation)
    - last_commit_date: Last commit date (system-managed)

    MUTABLE FIELDS (can be updated via API):
    - None (RepositoryVersion is typically immutable after creation)
    """

    version: Optional[VersionInfo] = Field(
        None, description="Version information with ref, sha, and metadata"
    )  # IMMUTABLE: Set at creation
    last_commit_date: Optional[datetime] = Field(
        None, description="The last known time when the repository version was updated"
    )  # IMMUTABLE: System-managed


class RepositoryVersion(BaseResource):
    """
    RepositoryVersion resource model extending BaseResource.

    OPERATION SUPPORT:
    ==================
    ✅ GET: List repository versions, Get by UUID
    ❌ CREATE: Not supported (managed by platform integrations)
    ❌ UPDATE: Not supported (repository versions are read-only)
    ❌ DELETE: Not supported (managed by platform integrations)

    FIELD MUTABILITY:
    =================
    IMMUTABLE FIELDS (read-only, system-managed):
    - uuid: Unique identifier
    - meta.name: Repository version name (set by platform)
    - spec.version: Version information (set by platform)
    - spec.last_commit_date: Last commit date (set by platform)
    - tenant_meta.namespace: Namespace assignment
    - All spec fields: Platform-managed metadata

    Note: Repository versions are automatically synchronized from platform integrations
    and cannot be manually created, updated, or deleted through the API.
    """

    # RepositoryVersion-specific fields (universal fields inherited from BaseResource)
    spec: RepositoryVersionSpec = Field(
        ..., description="RepositoryVersion specification"
    )  # type: ignore
    # Conditional attributes from Resource Guide example
    context: Optional[dict] = Field(
        None, description="Contextual information", alias="context"
    )
    scan_object: Optional[dict] = Field(
        None, description="Scan object information", alias="scan_object"
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data):
        # Convert spec to RepositoryVersionSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = RepositoryVersionSpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
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


def _get_repository_version_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for RepositoryVersion."""
    return BaseResourceOperations(client, "repository-versions", RepositoryVersion)


def list_repository_versions(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
    **kwargs,
) -> List[RepositoryVersion]:
    """List repository versions with advanced filtering and pagination."""
    ops = _get_repository_version_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)  # type: ignore


def get_repository_version(
    client: APIClient, tenant_meta_namespace: str, repository_version_uuid: str
) -> Optional[RepositoryVersion]:
    """Get specific repository version by UUID."""
    ops = _get_repository_version_ops(client)
    return ops.get(tenant_meta_namespace, repository_version_uuid)  # type: ignore


def create_repository_version(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: "CreateRepositoryVersionPayload",
) -> Optional[RepositoryVersion]:
    """Create a new repository version."""
    ops = _get_repository_version_ops(client)
    return ops.create(tenant_meta_namespace, payload)  # type: ignore


def update_repository_version(
    client: APIClient,
    tenant_meta_namespace: str,
    repository_version_uuid: str,
    payload: "UpdateRepositoryVersionPayload",
    update_mask: Optional[List[str]] = None,
) -> Optional[RepositoryVersion]:
    """Update an existing repository version with partial updates."""
    ops = _get_repository_version_ops(client)
    return ops.update(
        tenant_meta_namespace, repository_version_uuid, payload, update_mask
    )  # type: ignore


def delete_repository_version(
    client: APIClient, tenant_meta_namespace: str, repository_version_uuid: str
) -> bool:
    """Delete a repository version by UUID."""
    ops = _get_repository_version_ops(client)
    return ops.delete(tenant_meta_namespace, repository_version_uuid)  # type: ignore


# Payload models for create and update operations
class CreateRepositoryVersionPayload(BaseModel):
    """Payload for creating a repository version."""

    meta: "RepositoryVersionMetaCreate" = Field(
        ..., description="RepositoryVersion metadata for creation"
    )
    spec: RepositoryVersionSpec = Field(
        ..., description="RepositoryVersion specification"
    )


class UpdateRepositoryVersionPayload(BaseModel):
    """Payload for updating a repository version."""

    meta: Optional["RepositoryVersionMetaUpdate"] = Field(
        None, description="RepositoryVersion metadata for update"
    )
    spec: Optional[RepositoryVersionSpec] = Field(
        None, description="RepositoryVersion specification for update"
    )


class RepositoryVersionMetaCreate(BaseModel):
    """RepositoryVersion metadata for creation."""

    name: str = Field(..., description="RepositoryVersion name")
    description: Optional[str] = Field(
        None, description="RepositoryVersion description"
    )


class RepositoryVersionMetaUpdate(BaseModel):
    """RepositoryVersion metadata for update."""

    description: Optional[str] = Field(
        None, description="RepositoryVersion description"
    )
