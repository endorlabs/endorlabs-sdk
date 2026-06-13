"""Repository — thin consumer wrapper over generated V1Repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator

from endorlabs.generated.models.repository_service import V1Repository

from ..utils.logging_config import get_resource_logger
from .base import BaseMeta, BaseSpec, FlexibleEnum
from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin

logger = get_resource_logger(__name__)


class Repository(V1Repository, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for Repository (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("Repository")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("Repository")


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
                logger.warning("Unknown PlatformSource value: %s. Using as-is.", v)
                return v
        return v


class RepositoryMetaCreate(BaseModel):
    """Repository metadata for creation."""

    name: str = Field(..., description="Repository name")
    description: str | None = Field(None, description="Repository description")


class RepositoryMetaUpdate(BaseModel):
    """Repository metadata for update."""

    description: str | None = Field(None, description="Repository description")


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


def build_create_payload(**kwargs: Any) -> CreateRepositoryPayload:
    """Build CreateRepositoryPayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateRepositoryPayload, kwargs, attr_name="Repository"
    )
