"""DependencyMetadata resource module for Endor Labs API.

This module provides CRUD operations for DependencyMetadata resources following the
established patterns from the base class implementation.

IMPORTANT: All DependencyMetadata operations are hardcoded to use the "oss" namespace.
The tenant_meta_namespace parameter in all functions is kept for API compatibility
but is ignored - all operations always use the "oss" namespace regardless of the
parameter value passed.
"""

from __future__ import annotations

import logging
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

# Hardcoded namespace for DependencyMetadata operations
# All DependencyMetadata operations use the "oss" namespace regardless of
# the tenant_meta_namespace parameter passed to functions
DEPENDENCY_METADATA_NAMESPACE = "oss"


class DependencyScope(FlexibleEnum):
    """Dependency scope enumeration."""

    UNSPECIFIED = "DEPENDENCY_SCOPE_UNSPECIFIED"
    TEST = "DEPENDENCY_SCOPE_TEST"
    BUILD = "DEPENDENCY_SCOPE_BUILD"
    NORMAL = "DEPENDENCY_SCOPE_NORMAL"


class ReachabilityType(FlexibleEnum):
    """Reachability type enumeration."""

    UNSPECIFIED = "REACHABILITY_TYPE_UNSPECIFIED"
    REACHABLE = "REACHABILITY_TYPE_REACHABLE"
    UNREACHABLE = "REACHABILITY_TYPE_UNREACHABLE"
    UNKNOWN = "REACHABILITY_TYPE_UNKNOWN"


class ImportedType(FlexibleEnum):
    """Imported type enumeration."""

    UNSPECIFIED = "IMPORTED_TYPE_UNSPECIFIED"
    IN_SOURCE = "IMPORTED_TYPE_IN_SOURCE"
    NOT_IN_SOURCE = "IMPORTED_TYPE_NOT_IN_SOURCE"
    PHANTOM = "IMPORTED_TYPE_PHANTOM"
    SEGMENT_MATCH = "IMPORTED_TYPE_SEGMENT_MATCH"
    INSTALLED_IN_USE = "IMPORTED_TYPE_INSTALLED_IN_USE"


class DiscoveryType(FlexibleEnum):
    """Discovery type enumeration."""

    UNSPECIFIED = "DISCOVERY_TYPE_UNSPECIFIED"
    MANIFEST = "DISCOVERY_TYPE_MANIFEST"
    PHANTOM = "DISCOVERY_TYPE_PHANTOM"
    SEGMENT_MATCH = "DISCOVERY_TYPE_SEGMENT_MATCH"


class Ecosystem(FlexibleEnum):
    """Ecosystem enumeration."""

    UNSPECIFIED = "ECOSYSTEM_UNSPECIFIED"
    AI_MODEL = "ECOSYSTEM_AI_MODEL"
    APK = "ECOSYSTEM_APK"
    C = "ECOSYSTEM_C"
    CARGO = "ECOSYSTEM_CARGO"
    COCOAPOD = "ECOSYSTEM_COCOAPOD"
    CONTAINER = "ECOSYSTEM_CONTAINER"
    DEBIAN = "ECOSYSTEM_DEBIAN"
    GEM = "ECOSYSTEM_GEM"
    GIT = "ECOSYSTEM_GIT"
    GITHUB_ACTION = "ECOSYSTEM_GITHUB_ACTION"
    GO = "ECOSYSTEM_GO"
    HUGGING_FACE = "ECOSYSTEM_HUGGING_FACE"
    MAVEN = "ECOSYSTEM_MAVEN"
    NPM = "ECOSYSTEM_NPM"
    NUGET = "ECOSYSTEM_NUGET"
    PACKAGIST = "ECOSYSTEM_PACKAGIST"
    PYPI = "ECOSYSTEM_PYPI"
    RPM = "ECOSYSTEM_RPM"
    SBOM = "ECOSYSTEM_SBOM"
    SWIFT = "ECOSYSTEM_SWIFT"


class DependencyData(BaseModel):
    """Dependency data for DependencyMetadata."""

    project_uuid: str | None = Field(
        None, description="The UUID of the project to which the dependency belongs"
    )
    package_name: str = Field(
        ...,
        description="Qualified dependency package name. Does not include the version.",
    )
    package_version_uuid: str | None = Field(
        None, description="the UUID of the dependency package version object."
    )
    unresolved_version: str | None = Field(
        None, description="Unresolved dependency package version string."
    )
    resolved_version: str | None = Field(
        None, description="Resolved dependency package version."
    )
    ecosystem: Ecosystem | None = Field(None, description="Dependency ecosystem.")
    scope: DependencyScope | None = Field(None, description="Dependency scope.")
    reachability: ReachabilityType | None = Field(
        None, description="Dependency reachability."
    )
    utilization: float | None = Field(
        None, description="The fraction of the dependency that is used by this package."
    )
    imported_type: ImportedType | None = Field(None, description="Imported type.")
    discovery_type: DiscoveryType | None = Field(None, description="Discovery type.")


class ImporterData(BaseModel):
    """Importer data for DependencyMetadata."""

    project_uuid: str = Field(
        ..., description="The UUID of the project to which the root package belongs"
    )
    package_name: str = Field(
        ..., description="Qualified package name of the root package version."
    )
    package_version_uuid: str = Field(
        ..., description="The UUID of the importer package version object."
    )
    package_version_name: str = Field(
        ..., description="Fully qualified name of the root package version."
    )
    package_version_sha: str | None = Field(
        None,
        description="SHA of the source control version for the root package version.",
    )
    package_version_ref: str | None = Field(
        None,
        description="Resolved ref of the source control version for the root package.",
    )


class DependencyMetadataMeta(BaseMeta):
    """DependencyMetadata metadata extending BaseMeta."""

    # DependencyMetadata-specific fields only (universal fields inherited from BaseMeta)
    pass


class DependencyMetadataSpec(BaseSpec):
    """DependencyMetadata specification extending BaseSpec.

    Field Mutability Guide:
    ======================

    IMMUTABLE FIELDS (cannot be updated after creation):
    - dependency_data: Dependency information (set at creation)
    - importer_data: Importer information (set at creation)

    MUTABLE FIELDS (can be updated via API):
    - None (DependencyMetadata is typically immutable after creation)
    """

    dependency_data: DependencyData | None = Field(
        None, description="Information about the dependency"
    )  # IMMUTABLE: Set at creation
    importer_data: ImporterData | None = Field(
        None, description="Information about the root package version (importer)"
    )  # IMMUTABLE: Set at creation

    @field_validator("dependency_data", mode="before")
    @classmethod
    def validate_dependency_data(cls, v: Any) -> Any:
        """Handle dependency data validation."""
        if isinstance(v, dict):
            return DependencyData(**v)
        return v

    @field_validator("importer_data", mode="before")
    @classmethod
    def validate_importer_data(cls, v: Any) -> Any:
        """Handle importer data validation."""
        if isinstance(v, dict):
            return ImporterData(**v)
        return v


class DependencyMetadata(BaseResource):
    """DependencyMetadata resource model extending BaseResource.

    IMPORTANT: All DependencyMetadata operations are hardcoded to use
    the "oss" namespace. This resource always queries the OSS (Open Source
    Software) namespace regardless of the namespace parameter passed to
    the operation functions.
    """

    # DependencyMetadata-specific fields (universal fields inherited from BaseResource)
    spec: DependencyMetadataSpec = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        ..., description="DependencyMetadata specification"
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data: Any) -> None:
        # Convert spec to DependencyMetadataSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = DependencyMetadataSpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {"dependency_data", "importer_data"}
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v


def _get_dependency_metadata_ops(
    client: APIClient,
) -> BaseResourceOperations[DependencyMetadata]:
    """Get BaseResourceOperations instance for DependencyMetadata."""
    return BaseResourceOperations(client, "dependency-metadata", DependencyMetadata)


def list_dependency_metadata(
    client: APIClient,
    tenant_meta_namespace: str,  # Parameter kept for API compatibility but ignored
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[DependencyMetadata]:
    """List dependency metadata with advanced filtering and pagination.

    Note: This function hardcodes the namespace to "oss" regardless of the
    tenant_meta_namespace parameter value.
    """
    ops = _get_dependency_metadata_ops(client)
    return ops.list(DEPENDENCY_METADATA_NAMESPACE, list_params, max_pages, **kwargs)


def get_dependency_metadata(
    client: APIClient,
    tenant_meta_namespace: str,  # Parameter kept for API compatibility but ignored
    dependency_metadata_uuid: str,
) -> DependencyMetadata:
    """Get specific dependency metadata by UUID.

    Note: This function hardcodes the namespace to "oss" regardless of the
    tenant_meta_namespace parameter value.

    Raises:
        NotFoundError: If dependency metadata doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    ops = _get_dependency_metadata_ops(client)
    return ops.get(DEPENDENCY_METADATA_NAMESPACE, dependency_metadata_uuid)


def create_dependency_metadata(
    client: APIClient,
    tenant_meta_namespace: str,  # Parameter kept for API compatibility but ignored
    payload: CreateDependencyMetadataPayload,
) -> DependencyMetadata:
    """Create a new dependency metadata with pre-validation and typed errors.

    Note: This function hardcodes the namespace to "oss" regardless of the
    tenant_meta_namespace parameter value.

    Raises:
        ValidationError: If payload is invalid
        NotFoundError: If namespace doesn't exist
        PermissionDeniedError: If user lacks permission
        ConflictError: If dependency metadata already exists
        ServerError: If server error occurs

    """
    ops = _get_dependency_metadata_ops(client)
    return ops.create(DEPENDENCY_METADATA_NAMESPACE, payload)


def update_dependency_metadata(
    client: APIClient,
    tenant_meta_namespace: str,  # Parameter kept for API compatibility but ignored
    dependency_metadata_uuid: str,
    payload: UpdateDependencyMetadataPayload,
    update_mask: str | None = None,
) -> DependencyMetadata | None:
    """Update an existing dependency metadata with partial updates.

    Note: This function hardcodes the namespace to "oss" regardless of the
    tenant_meta_namespace parameter value.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Parameter kept for API compatibility but ignored
        dependency_metadata_uuid: UUID of the dependency metadata to update
        payload: DependencyMetadata update payload
        update_mask: Optional comma-separated list of fields to update
            (e.g., "meta.tags,meta.description"). If provided, only these
            fields will be updated. If omitted, all non-None fields in
            payload will be updated.

    Returns:
        Updated DependencyMetadata object

    Raises:
        ValidationError: If payload is invalid
        NotFoundError: If dependency metadata doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    # Convert update_mask from string to List[str] for base class
    update_mask_list = (
        [field.strip() for field in update_mask.split(",")] if update_mask else None
    )
    ops = _get_dependency_metadata_ops(client)
    return ops.update(
        DEPENDENCY_METADATA_NAMESPACE,
        dependency_metadata_uuid,
        payload,
        update_mask_list,
    )


def delete_dependency_metadata(
    client: APIClient,
    tenant_meta_namespace: str,  # Parameter kept for API compatibility but ignored
    dependency_metadata_uuid: str,
) -> bool:
    """Delete a dependency metadata by UUID.

    Note: This function hardcodes the namespace to "oss" regardless of the
    tenant_meta_namespace parameter value.
    """
    ops = _get_dependency_metadata_ops(client)
    return ops.delete(DEPENDENCY_METADATA_NAMESPACE, dependency_metadata_uuid)


# Payload models for create and update operations
class CreateDependencyMetadataPayload(BaseModel):
    """Payload for creating a dependency metadata."""

    meta: DependencyMetadataMetaCreate = Field(
        ..., description="DependencyMetadata metadata for creation"
    )
    spec: DependencyMetadataSpec = Field(
        ..., description="DependencyMetadata specification"
    )


class UpdateDependencyMetadataPayload(BaseModel):
    """Payload for updating a dependency metadata."""

    meta: DependencyMetadataMetaUpdate | None = Field(
        None, description="DependencyMetadata metadata for update"
    )
    spec: DependencyMetadataSpec | None = Field(
        None, description="DependencyMetadata specification for update"
    )


class DependencyMetadataMetaCreate(BaseModel):
    """DependencyMetadata metadata for creation."""

    name: str = Field(..., description="DependencyMetadata name")
    description: str | None = Field(None, description="DependencyMetadata description")


class DependencyMetadataMetaUpdate(BaseModel):
    """DependencyMetadata metadata for update."""

    description: str | None = Field(None, description="DependencyMetadata description")
