"""
Installation resource module for Endor Labs API.

This module provides CRUD operations for Installation resources following the
established patterns from the base class implementation.
"""

import logging
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseResourceOperations,
    BaseSpec,
    FlexibleEnum,
)
from ..types import ListParameters

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


class EnabledFeatureType(FlexibleEnum):
    """Enabled feature type enumeration."""

    GIT = "GIT"
    GITHUB = "GITHUB"


class PlatformSourceType(FlexibleEnum):
    """Platform source type enumeration."""

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


class GitHubConfig(BaseModel):
    """GitHub configuration for installation."""

    app_id: str = Field(..., description="GitHub App ID")
    installation_id: str = Field(..., description="GitHub Installation ID")
    private_key: str = Field(..., description="GitHub App Private Key")


class AzureConfig(BaseModel):
    """Azure configuration for installation."""

    tenant_id: str = Field(..., description="Azure Tenant ID")
    client_id: str = Field(..., description="Azure Client ID")
    client_secret: str = Field(..., description="Azure Client Secret")


class GitLabConfig(BaseModel):
    """GitLab configuration for installation."""

    instance_url: str = Field(..., description="GitLab Instance URL")
    access_token: str = Field(..., description="GitLab Access Token")


class BitBucketConfig(BaseModel):
    """BitBucket configuration for installation."""

    workspace: str = Field(..., description="BitBucket Workspace")
    access_token: str = Field(..., description="BitBucket Access Token")


class InstallationMeta(BaseMeta):
    """Installation metadata extending BaseMeta."""

    # Installation-specific fields only (universal fields inherited from BaseMeta)
    pass


class InstallationSpec(BaseSpec):
    """Installation specification extending BaseSpec.

    Field Mutability Guide:
    ======================

    IMMUTABLE FIELDS (cannot be updated after creation):
    - external_id: External ID (set at creation)
    - external_name: External name (read-only)
    - user: User name (read-only)
    - ingestion_time: Ingestion time (read-only)
    - target_type: Target type (read-only)
    - login: Login (read-only)
    - ingestion_token: Ingestion token (read-only)
    - platform_source: Platform source (deprecated, read-only)
    - platform_type: Platform type (set at creation)
    - github_config: GitHub config (set at creation)
    - azure_config: Azure config (set at creation)
    - gitlab_config: GitLab config (set at creation)
    - bitbucket_config: BitBucket config (set at creation)
    - marked_for_deletion: Marked for deletion (read-only)

    MUTABLE FIELDS (can be updated via API):
    - public: Public flag (can be updated)
    - suspended: Suspended flag (can be updated)
    - project_uuids: Project UUIDs (can be updated)
    - invalid: Invalid flag (can be updated)
    - enabled_features: Enabled features (can be updated)
    - include_archived_repos: Include archived repos (can be updated)
    - installation_error_message: Error message (can be updated)
    """

    public: Optional[bool] = Field(
        None, description="Apply only to public repositories. Default value is false"
    )  # MUTABLE: Can be updated
    external_id: Optional[str] = Field(
        None, description="The external ID of the installation"
    )  # IMMUTABLE: Set at creation
    external_name: Optional[str] = Field(
        None, description="The external name of the installation"
    )  # IMMUTABLE: Read-only
    user: Optional[str] = Field(
        None, description="The user name of the user that initiated the installation"
    )  # IMMUTABLE: Read-only
    ingestion_time: Optional[datetime] = Field(
        None, description="The last time that we ingested the installation data"
    )  # IMMUTABLE: Read-only
    target_type: Optional[str] = Field(
        None, description="The target of the installation (Organization or User)"
    )  # IMMUTABLE: Read-only
    suspended: Optional[bool] = Field(
        None, description="Indicates if the installation is suspended"
    )  # MUTABLE: Can be updated
    project_uuids: Optional[List[str]] = Field(
        None,
        description="The list of projects that are associated with this installation",
    )  # MUTABLE: Can be updated
    login: Optional[str] = Field(
        None,
        description="The login of the account taken directly from the GitHub response",
    )  # IMMUTABLE: Read-only
    invalid: Optional[bool] = Field(
        None,
        description="Identifies installations with potentially removed config",
    )  # MUTABLE: Can be updated
    ingestion_token: Optional[str] = Field(
        None,
        description="API token for scanner to use for scanning installation info",
    )  # IMMUTABLE: Read-only
    enabled_features: Optional[List[EnabledFeatureType]] = Field(
        None, description="Enabled features. The valid values are 'git, github'"
    )  # MUTABLE: Can be updated
    platform_source: Optional[PlatformSourceType] = Field(
        None, description="Deprecated: Use platform_type instead"
    )  # IMMUTABLE: Read-only
    platform_type: Optional[PlatformSourceType] = Field(
        None,
        description="Platform type: GitHub, GitLab, Azure, or Bitbucket",
    )  # IMMUTABLE: Set at creation
    github_config: Optional[GitHubConfig] = Field(
        None, description="GitHub configuration"
    )  # IMMUTABLE: Set at creation
    azure_config: Optional[AzureConfig] = Field(
        None, description="Azure configuration"
    )  # IMMUTABLE: Set at creation
    gitlab_config: Optional[GitLabConfig] = Field(
        None, description="GitLab configuration"
    )  # IMMUTABLE: Set at creation
    bitbucket_config: Optional[BitBucketConfig] = Field(
        None, description="BitBucket configuration"
    )  # IMMUTABLE: Set at creation
    marked_for_deletion: Optional[bool] = Field(
        None, description="Indicates the installation is marked for deletion"
    )  # IMMUTABLE: Read-only
    include_archived_repos: Optional[bool] = Field(
        None,
        description="Boolean indicating if archived repos should be included",
    )  # MUTABLE: Can be updated
    installation_error_message: Optional[str] = Field(
        None, description="Message explaining why the installation is invalid"
    )  # MUTABLE: Can be updated

    @field_validator("enabled_features", mode="before")
    @classmethod
    def validate_enabled_features(cls, v):
        """Handle enabled features validation."""
        if isinstance(v, list):
            validated_features = []
            for feature in v:
                if isinstance(feature, str):
                    try:
                        validated_features.append(EnabledFeatureType(feature))
                    except ValueError:
                        logger.warning(
                            f"Unknown EnabledFeatureType value: {feature}. Using as-is."
                        )
                        validated_features.append(feature)
                else:
                    validated_features.append(feature)
            return validated_features
        return v

    @field_validator("platform_source", mode="before")
    @classmethod
    def validate_platform_source(cls, v):
        """Handle unknown platform source values gracefully."""
        if isinstance(v, str):
            try:
                return PlatformSourceType(v)
            except ValueError:
                logger.warning(f"Unknown PlatformSourceType value: {v}. Using as-is.")
                return v
        return v

    @field_validator("platform_type", mode="before")
    @classmethod
    def validate_platform_type(cls, v):
        """Handle unknown platform type values gracefully."""
        if isinstance(v, str):
            try:
                return PlatformSourceType(v)
            except ValueError:
                logger.warning(f"Unknown PlatformSourceType value: {v}. Using as-is.")
                return v
        return v


class Installation(BaseResource):
    """Installation resource model extending BaseResource."""

    # Installation-specific fields (universal fields inherited from BaseResource)
    spec: InstallationSpec = Field(..., description="Installation specification")  # type: ignore

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data):
        # Convert spec to InstallationSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = InstallationSpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "public",
                "external_id",
                "external_name",
                "user",
                "ingestion_time",
                "target_type",
                "suspended",
                "project_uuids",
                "login",
                "invalid",
                "ingestion_token",
                "enabled_features",
                "platform_source",
                "platform_type",
                "github_config",
                "azure_config",
                "gitlab_config",
                "bitbucket_config",
                "marked_for_deletion",
                "include_archived_repos",
                "installation_error_message",
            }
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v


def _get_installation_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for Installation."""
    return BaseResourceOperations(client, "installations", Installation)


def list_installations(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
    **kwargs,
) -> List[Installation]:
    """List installations with advanced filtering and pagination."""
    ops = _get_installation_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)  # type: ignore


def get_installation(
    client: APIClient, tenant_meta_namespace: str, installation_uuid: str
) -> Optional[Installation]:
    """Get specific installation by UUID."""
    ops = _get_installation_ops(client)
    return ops.get(tenant_meta_namespace, installation_uuid)  # type: ignore


def create_installation(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: "CreateInstallationPayload",
) -> Optional[Installation]:
    """Create a new installation."""
    ops = _get_installation_ops(client)
    return ops.create(tenant_meta_namespace, payload)  # type: ignore


def update_installation(
    client: APIClient,
    tenant_meta_namespace: str,
    installation_uuid: str,
    payload: "UpdateInstallationPayload",
    update_mask: Optional[List[str]] = None,
) -> Optional[Installation]:
    """Update an existing installation with partial updates."""
    ops = _get_installation_ops(client)
    return ops.update(tenant_meta_namespace, installation_uuid, payload, update_mask)  # type: ignore


def delete_installation(
    client: APIClient, tenant_meta_namespace: str, installation_uuid: str
) -> bool:
    """Delete an installation by UUID."""
    ops = _get_installation_ops(client)
    return ops.delete(tenant_meta_namespace, installation_uuid)  # type: ignore


# Payload models for create and update operations
class CreateInstallationPayload(BaseModel):
    """Payload for creating an installation."""

    meta: "InstallationMetaCreate" = Field(
        ..., description="Installation metadata for creation"
    )
    spec: InstallationSpec = Field(..., description="Installation specification")


class UpdateInstallationPayload(BaseModel):
    """Payload for updating an installation."""

    meta: Optional["InstallationMetaUpdate"] = Field(
        None, description="Installation metadata for update"
    )
    spec: Optional[InstallationSpec] = Field(
        None, description="Installation specification for update"
    )


class InstallationMetaCreate(BaseModel):
    """Installation metadata for creation."""

    name: str = Field(..., description="Installation name")
    description: Optional[str] = Field(None, description="Installation description")


class InstallationMetaUpdate(BaseModel):
    """Installation metadata for update."""

    description: Optional[str] = Field(None, description="Installation description")
