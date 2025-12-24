"""
DependencyMetadata resource module for Endor Labs API.

This module provides CRUD operations for DependencyMetadata resources following the
established patterns from the base class implementation.
"""

import logging
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
    GO = "ECOSYSTEM_GO"
    MAVEN = "ECOSYSTEM_MAVEN"
    PYPI = "ECOSYSTEM_PYPI"
    CARGO = "ECOSYSTEM_CARGO"
    NPM = "ECOSYSTEM_NPM"
    GEM = "ECOSYSTEM_GEM"
    NUGET = "ECOSYSTEM_NUGET"
    PACKAGIST = "ECOSYSTEM_PACKAGIST"
    SBOM = "ECOSYSTEM_SBOM"
    RPM = "ECOSYSTEM_RPM"
    DEBIAN = "ECOSYSTEM_DEBIAN"
    GITHUB_ACTION = "ECOSYSTEM_GITHUB_ACTION"


class DependencyData(BaseModel):
    """Dependency data for DependencyMetadata."""

    project_uuid: Optional[str] = Field(
        None, description="The UUID of the project to which the dependency belongs"
    )
    package_name: str = Field(
        ...,
        description="Qualified dependency package name. Does not include the version.",
    )
    package_version_uuid: Optional[str] = Field(
        None, description="the UUID of the dependency package version object."
    )
    unresolved_version: Optional[str] = Field(
        None, description="Unresolved dependency package version string."
    )
    resolved_version: Optional[str] = Field(
        None, description="Resolved dependency package version."
    )
    ecosystem: Optional[Ecosystem] = Field(None, description="Dependency ecosystem.")
    scope: Optional[DependencyScope] = Field(None, description="Dependency scope.")
    reachability: Optional[ReachabilityType] = Field(
        None, description="Dependency reachability."
    )
    utilization: Optional[float] = Field(
        None, description="The fraction of the dependency that is used by this package."
    )
    imported_type: Optional[ImportedType] = Field(None, description="Imported type.")
    discovery_type: Optional[DiscoveryType] = Field(None, description="Discovery type.")


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
    package_version_sha: Optional[str] = Field(
        None,
        description="SHA of the source control version for the root package version.",
    )
    package_version_ref: Optional[str] = Field(
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

    dependency_data: Optional[DependencyData] = Field(
        None, description="Information about the dependency"
    )  # IMMUTABLE: Set at creation
    importer_data: Optional[ImporterData] = Field(
        None, description="Information about the root package version (importer)"
    )  # IMMUTABLE: Set at creation

    @field_validator("dependency_data", mode="before")
    @classmethod
    def validate_dependency_data(cls, v):
        """Handle dependency data validation."""
        if isinstance(v, dict):
            return DependencyData(**v)
        return v

    @field_validator("importer_data", mode="before")
    @classmethod
    def validate_importer_data(cls, v):
        """Handle importer data validation."""
        if isinstance(v, dict):
            return ImporterData(**v)
        return v


class DependencyMetadata(BaseResource):
    """DependencyMetadata resource model extending BaseResource."""

    # DependencyMetadata-specific fields (universal fields inherited from BaseResource)
    spec: DependencyMetadataSpec = Field(
        ..., description="DependencyMetadata specification"
    )  # type: ignore

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data):
        # Convert spec to DependencyMetadataSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = DependencyMetadataSpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
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


def _get_dependency_metadata_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for DependencyMetadata."""
    return BaseResourceOperations(client, "dependency-metadata", DependencyMetadata)


def list_dependency_metadata(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
    **kwargs,
) -> List[DependencyMetadata]:
    """List dependency metadata with advanced filtering and pagination."""
    ops = _get_dependency_metadata_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)  # type: ignore


def get_dependency_metadata(
    client: APIClient, tenant_meta_namespace: str, dependency_metadata_uuid: str
) -> Optional[DependencyMetadata]:
    """Get specific dependency metadata by UUID."""
    ops = _get_dependency_metadata_ops(client)
    return ops.get(tenant_meta_namespace, dependency_metadata_uuid)  # type: ignore


def create_dependency_metadata(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: "CreateDependencyMetadataPayload",
) -> Optional[DependencyMetadata]:
    """Create a new dependency metadata."""
    ops = _get_dependency_metadata_ops(client)
    return ops.create(tenant_meta_namespace, payload)  # type: ignore


def update_dependency_metadata(
    client: APIClient,
    tenant_meta_namespace: str,
    dependency_metadata_uuid: str,
    payload: "UpdateDependencyMetadataPayload",
    update_mask: Optional[List[str]] = None,
) -> Optional[DependencyMetadata]:
    """Update an existing dependency metadata with partial updates."""
    ops = _get_dependency_metadata_ops(client)
    return ops.update(
        tenant_meta_namespace, dependency_metadata_uuid, payload, update_mask
    )  # type: ignore


def delete_dependency_metadata(
    client: APIClient, tenant_meta_namespace: str, dependency_metadata_uuid: str
) -> bool:
    """Delete a dependency metadata by UUID."""
    ops = _get_dependency_metadata_ops(client)
    return ops.delete(tenant_meta_namespace, dependency_metadata_uuid)  # type: ignore


# Payload models for create and update operations
class CreateDependencyMetadataPayload(BaseModel):
    """Payload for creating a dependency metadata."""

    meta: "DependencyMetadataMetaCreate" = Field(
        ..., description="DependencyMetadata metadata for creation"
    )
    spec: DependencyMetadataSpec = Field(
        ..., description="DependencyMetadata specification"
    )


class UpdateDependencyMetadataPayload(BaseModel):
    """Payload for updating a dependency metadata."""

    meta: Optional["DependencyMetadataMetaUpdate"] = Field(
        None, description="DependencyMetadata metadata for update"
    )
    spec: Optional[DependencyMetadataSpec] = Field(
        None, description="DependencyMetadata specification for update"
    )


class DependencyMetadataMetaCreate(BaseModel):
    """DependencyMetadata metadata for creation."""

    name: str = Field(..., description="DependencyMetadata name")
    description: Optional[str] = Field(
        None, description="DependencyMetadata description"
    )


class DependencyMetadataMetaUpdate(BaseModel):
    """DependencyMetadata metadata for update."""

    description: Optional[str] = Field(
        None, description="DependencyMetadata description"
    )
