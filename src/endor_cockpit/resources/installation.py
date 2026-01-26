"""
Installation resource module for Endor Labs API.

This module provides CRUD operations for Installation resources following the
established patterns from the base class implementation.

API OPERATIONS SUPPORTED:
- GET: List installations, Get installation by UUID

API LIMITATIONS:
- CREATE: Not supported by API (installations managed by platform integrations)
- UPDATE: Not supported by API (installation configuration is read-only)
- DELETE: Not supported by API (installations managed by platform integrations)

Note: Installations are auto-discovered and managed through platform
integrations (GitHub, GitLab, Azure, Bitbucket) and cannot be manually
created, updated, or deleted.
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
    installation_id: Optional[str] = Field(
        None, description="GitHub Installation ID (may be masked in API responses)"
    )
    private_key: Optional[str] = Field(
        None, description="GitHub App Private Key (may be masked in API responses)"
    )


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
    scm_app_uuid: Optional[str] = Field(
        None, description="The UUID of the SCM app being installed"
    )  # IMMUTABLE: Set at creation

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
    """
    Installation resource model extending BaseResource.

    OPERATION SUPPORT:
    ==================
    ✅ GET: List installations, Get by UUID
    ✅ UPDATE: Update installation configuration (limited fields)
    ❌ CREATE: Not supported (managed by platform integrations)
    ❌ DELETE: Not supported (managed by platform integrations)

    FIELD MUTABILITY (per OpenAPI spec):
    =====================================
    IMMUTABLE FIELDS (readOnly: true in API spec):
    - uuid: Unique identifier (readOnly: true in UpdateInstallation request body)
    - meta.create_time, meta.update_time, meta.upsert_time: Timestamps
      (readOnly: true in v1Meta)
    - meta.kind, meta.version: Resource metadata (readOnly: true in v1Meta)
    - meta.created_by, meta.updated_by: Audit fields (readOnly: true in v1Meta)
    - meta.references, meta.index_data: System-managed fields (readOnly: true in v1Meta)
    - spec.external_name: External name (readOnly: true in v1InstallationSpec)
    - spec.user: User name (readOnly: true in v1InstallationSpec)
    - spec.ingestion_time: Ingestion time (readOnly: true in v1InstallationSpec)
    - spec.target_type: Target type (readOnly: true in v1InstallationSpec)
    - spec.login: Login (readOnly: true in v1InstallationSpec)
    - spec.ingestion_token: Ingestion token (readOnly: true in v1InstallationSpec)
    - spec.marked_for_deletion: Marked for deletion
      (readOnly: true in v1InstallationSpec)
    - tenant_meta.namespace: Namespace assignment

    MUTABLE FIELDS (NOT readOnly in API spec):
    - meta.name, meta.description, meta.tags: Metadata
    - spec.public: Public flag
    - spec.external_id: External ID
    - spec.suspended: Suspended flag
    - spec.project_uuids: Project UUIDs list
    - spec.invalid: Invalid flag
    - spec.enabled_features: Enabled features list
    - spec.platform_source: Platform source (deprecated but mutable)
    - spec.platform_type: Platform type
    - spec.github_config, spec.azure_config, spec.gitlab_config,
      spec.bitbucket_config: Platform configs
    - spec.include_archived_repos: Include archived repos flag
    - spec.installation_error_message: Error message
    - processing_status.*: All processing status fields
    - propagate: Whether to propagate to child namespaces

    Note: Installations are automatically synchronized from platform integrations
    but certain configuration fields can be updated through the API.
    """

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
                "scm_app_uuid",
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
    max_pages: Optional[int] = None,
    **kwargs,
) -> List[Installation]:
    """List installations with advanced filtering and pagination."""
    ops = _get_installation_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)  # type: ignore


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
    """
    Update an existing installation with partial updates.

    This function supports updating only specific fields using the update_mask
    parameter, which enables efficient partial updates without overwriting
    unchanged fields.

    MUTABLE FIELDS:
    - meta.description: Installation description
    - spec.public: Public flag
    - spec.suspended: Suspended flag
    - spec.project_uuids: Project UUIDs list
    - spec.invalid: Invalid flag
    - spec.enabled_features: Enabled features list
    - spec.include_archived_repos: Include archived repos flag
    - spec.installation_error_message: Error message
    - processing_status.scan_state: Scan state
      (e.g., SCAN_STATE_IDLE, SCAN_STATE_INGESTING)
    - processing_status.disable_automated_scan: Disable automated scanning flag

    FIELD MUTABILITY (per OpenAPI spec):
    =====================================
    IMMUTABLE FIELDS (readOnly: true in API spec):
    - uuid: Unique identifier (readOnly: true in UpdateInstallation request body)
    - meta.create_time, meta.update_time, meta.upsert_time: Timestamps
      (readOnly: true in v1Meta)
    - meta.kind, meta.version: Resource metadata (readOnly: true in v1Meta)
    - meta.created_by, meta.updated_by: Audit fields (readOnly: true in v1Meta)
    - meta.references, meta.index_data: System-managed fields (readOnly: true in v1Meta)
    - spec.external_name: External name (readOnly: true in v1InstallationSpec)
    - spec.user: User name (readOnly: true in v1InstallationSpec)
    - spec.ingestion_time: Ingestion time (readOnly: true in v1InstallationSpec)
    - spec.target_type: Target type (readOnly: true in v1InstallationSpec)
    - spec.login: Login (readOnly: true in v1InstallationSpec)
    - spec.ingestion_token: Ingestion token (readOnly: true in v1InstallationSpec)
    - spec.marked_for_deletion: Marked for deletion
      (readOnly: true in v1InstallationSpec)
    - tenant_meta.namespace: Namespace assignment

    MUTABLE FIELDS (NOT readOnly in API spec):
    - meta.name, meta.description, meta.tags: Metadata
    - spec.public: Public flag
    - spec.external_id: External ID
    - spec.suspended: Suspended flag
    - spec.project_uuids: Project UUIDs list
    - spec.invalid: Invalid flag
    - spec.enabled_features: Enabled features list
    - spec.platform_source: Platform source (deprecated but mutable)
    - spec.platform_type: Platform type
    - spec.github_config, spec.azure_config, spec.gitlab_config,
      spec.bitbucket_config: Platform configs
    - spec.include_archived_repos: Include archived repos flag
    - spec.installation_error_message: Error message
    - processing_status.*: All processing status fields
    - propagate: Whether to propagate to child namespaces

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        installation_uuid: UUID of the installation to update
        payload: Installation update payload
        update_mask: Optional list of fields to update

    Returns:
        Updated Installation object if successful, None otherwise
    """
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
    """
    Payload for updating an installation.

    MUTABLE FIELDS (can be updated via PATCH):
    - meta.description: Installation description
    - spec.public: Public flag
    - spec.suspended: Suspended flag
    - spec.project_uuids: Project UUIDs list
    - spec.invalid: Invalid flag
    - spec.enabled_features: Enabled features list
    - spec.include_archived_repos: Include archived repos flag
    - spec.installation_error_message: Error message
    - processing_status.scan_state: Scan state
      (e.g., SCAN_STATE_IDLE, SCAN_STATE_INGESTING)
    - processing_status.disable_automated_scan: Disable automated scanning flag

    IMMUTABLE FIELDS (read-only, managed by API):
    - uuid: Unique identifier (set at creation)
    - meta.name: Installation name (set by platform)
    - spec.external_id: External ID (set at creation)
    - spec.external_name: External name (read-only)
    - spec.user: User name (read-only)
    - spec.ingestion_time: Ingestion time (read-only)
    - spec.target_type: Target type (read-only)
    - spec.login: Login (read-only)
    - spec.ingestion_token: Ingestion token (read-only)
    - spec.platform_source: Platform source (deprecated, read-only)
    - spec.platform_type: Platform type (set at creation)
    - spec.marked_for_deletion: Marked for deletion (read-only)
    - tenant_meta.namespace: Namespace assignment
    - processing_status.scan_time: Last scan time (system-managed)
    - processing_status.analytic_time: Last analytics time (system-managed)
    """

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
