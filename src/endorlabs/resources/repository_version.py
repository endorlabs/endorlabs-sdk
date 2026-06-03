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

from datetime import datetime
from typing import Any, override

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.base import BaseMeta, BaseResource, BaseSpec
from ..utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)


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


class ScanObject(BaseModel):
    """Scan object information for a repository version."""

    status: str | None = Field(None, description="Scan status.")
    scan_time: str | None = Field(None, description="Last scan time.")
    aisast_status: dict[str, Any] | None = Field(
        None,
        description="AI SAST indexing status (e.g. last_full_index_sha).",
    )
    endor_ignore_file_hash_map: dict[str, Any] | None = Field(
        None,
        description="Map of endor ignore file hashes.",
    )

    model_config = ConfigDict(extra="allow")


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
    scan_object: ScanObject | dict[str, Any] | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
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
                    "Schema drift detected in %s: unknown fields %s",
                    info.field_name,
                    unknown_fields,
                )
        return v

    @override
    @classmethod
    def get_mutable_fields_cls(cls) -> list[str]:
        """Get list of mutable fields for RepositoryVersion."""
        return ["meta.name", "meta.description", "meta.tags", "spec"]


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
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateRepositoryVersionPayload, kwargs, attr_name="RepositoryVersion"
    )


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
