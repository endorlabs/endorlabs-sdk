"""RepositoryVersion — thin consumer wrapper over generated V1RepositoryVersion."""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from endorlabs.generated.models.repository_version_service import V1RepositoryVersion

from .base import BaseMeta, BaseSpec
from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class RepositoryVersion(
    V1RepositoryVersion, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for RepositoryVersion (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("RepositoryVersion")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("RepositoryVersion")


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


class RepositoryVersionMetaCreate(BaseModel):
    """RepositoryVersion metadata for creation."""

    name: str = Field(..., description="RepositoryVersion name")
    description: str | None = Field(None, description="RepositoryVersion description")


class RepositoryVersionMetaUpdate(BaseModel):
    """RepositoryVersion metadata for update."""

    description: str | None = Field(None, description="RepositoryVersion description")


class CreateRepositoryVersionPayload(BaseModel):
    """Payload for creating a repository version."""

    meta: RepositoryVersionMetaCreate = Field(
        ..., description="RepositoryVersion metadata for creation"
    )
    spec: RepositoryVersionSpec = Field(
        ..., description="RepositoryVersion specification"
    )


class UpdateRepositoryVersionPayload(BaseModel):
    """Payload for updating a repository version."""

    meta: RepositoryVersionMetaUpdate | None = Field(
        None, description="RepositoryVersion metadata for update"
    )
    spec: RepositoryVersionSpec | None = Field(
        None, description="RepositoryVersion specification for update"
    )


def build_create_payload(**kwargs: Any) -> CreateRepositoryVersionPayload:
    """Build CreateRepositoryVersionPayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateRepositoryVersionPayload, kwargs, attr_name="RepositoryVersion"
    )
