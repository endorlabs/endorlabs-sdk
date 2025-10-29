"""
PackageVersion resource module for Endor Labs API.

This module provides CRUD operations for PackageVersion resources following the
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


class Language(FlexibleEnum):
    """Language enumeration."""

    UNSPECIFIED = "LANGUAGE_UNSPECIFIED"
    GO = "LANGUAGE_GO"
    JAVA = "LANGUAGE_JAVA"
    SCALA = "LANGUAGE_SCALA"
    PYTHON = "LANGUAGE_PYTHON"
    RUST = "LANGUAGE_RUST"
    JS = "LANGUAGE_JS"
    RUBY = "LANGUAGE_RUBY"
    CSHARP = "LANGUAGE_CSHARP"
    PHP = "LANGUAGE_PHP"
    TYPESCRIPT = "LANGUAGE_TYPESCRIPT"
    KOTLIN = "LANGUAGE_KOTLIN"
    SWIFT = "LANGUAGE_SWIFT"


class PackageVersionSourceCodeReference(BaseModel):
    """Source code reference for package version."""

    ref: str = Field(..., description="Reference (branch, tag, or commit)")
    sha: Optional[str] = Field(None, description="Commit SHA")
    repository_uuid: Optional[str] = Field(None, description="Repository UUID")


class PackageVersionDependency(BaseModel):
    """Package version dependency."""

    name: str = Field(..., description="Dependency name")
    version: str = Field(..., description="Dependency version")
    ecosystem: Optional[Ecosystem] = Field(None, description="Dependency ecosystem")


class Bom(BaseModel):
    """Bill of Materials for resolved dependencies."""

    dependencies: List[PackageVersionDependency] = Field(
        ..., description="Resolved dependencies"
    )


class PackageVersionResolutionErrors(BaseModel):
    """Resolution errors for package version."""

    errors: List[str] = Field(..., description="List of resolution errors")


class ContainerMetadata(BaseModel):
    """Container metadata."""

    image_name: str = Field(..., description="Container image name")
    tag: Optional[str] = Field(None, description="Container tag")
    digest: Optional[str] = Field(None, description="Container digest")


class BazelMetadata(BaseModel):
    """Bazel metadata."""

    target: str = Field(..., description="Bazel target")
    package: Optional[str] = Field(None, description="Bazel package")


class CodeOwnerData(BaseModel):
    """Code owner data."""

    owners: List[str] = Field(..., description="List of code owners")
    paths: List[str] = Field(..., description="List of owned paths")


class PrecomputedState(BaseModel):
    """Precomputed state for call graph."""

    state: str = Field(..., description="Precomputed state")
    timestamp: Optional[datetime] = Field(None, description="State timestamp")


class PackageVersionMeta(BaseMeta):
    """PackageVersion metadata extending BaseMeta."""

    # PackageVersion-specific fields only (universal fields inherited from BaseMeta)
    pass


class PackageVersionSpec(BaseSpec):
    """PackageVersion specification extending BaseSpec.

    Field Mutability Guide:
    ======================

    IMMUTABLE FIELDS (cannot be updated after creation):
    - project_uuid: Project assignment (set at creation)
    - source_code_reference: Source code reference (set at creation)
    - release_timestamp: Release timestamp (set at creation)
    - ecosystem: Package ecosystem (analysis-determined)
    - package_name: Package name (analysis-determined)
    - language: Programming language (analysis-determined)
    - relative_path: Relative path (set at creation)
    - container_metadata: Container metadata (analysis-determined)
    - bazel_metadata: Bazel metadata (analysis-determined)
    - code_owners: Code owner data (analysis-determined)
    - internal_reference_key: Internal reference key (system-generated)
    - precomputed_call_graph_state: Precomputed state (system-managed)

    MUTABLE FIELDS (can be updated via API):
    - unresolved_dependencies: Dependency declarations (can be updated)
    - resolved_dependencies: Resolved dependency graph (can be updated)
    - resolution_errors: Resolution errors (can be updated)
    - call_graph_available: Call graph availability (can be updated)
    """

    project_uuid: str = Field(
        ..., description="The UUID of the project to which this package version belongs"
    )  # IMMUTABLE: Set at creation
    source_code_reference: Optional[PackageVersionSourceCodeReference] = Field(
        None,
        description="Ref info of source code repository from which package was created",
    )  # IMMUTABLE: Set at creation
    release_timestamp: Optional[datetime] = Field(
        None,
        description="Release timestamp when this package version was released",
    )  # IMMUTABLE: Set at creation
    unresolved_dependencies: Optional[List[PackageVersionDependency]] = Field(
        None,
        description="Exact dependency declarations in package manager descriptor file",
    )  # MUTABLE: Can be updated
    resolved_dependencies: Optional[Bom] = Field(
        None, description="A graph of resolved dependencies"
    )  # MUTABLE: Can be updated
    resolution_errors: Optional[PackageVersionResolutionErrors] = Field(
        None, description="Captures any errors during dependency resolution"
    )  # MUTABLE: Can be updated
    ecosystem: Optional[Ecosystem] = Field(
        None, description="Dependency ecosystem"
    )  # IMMUTABLE: Analysis-determined
    package_name: Optional[str] = Field(
        None, description="The name of the package of this package version"
    )  # IMMUTABLE: Analysis-determined
    language: Optional[Language] = Field(
        None, description="Language of the package_version"
    )  # IMMUTABLE: Analysis-determined
    relative_path: Optional[str] = Field(
        None,
        description="Relative path of package from discovery point to workspace root",
    )  # IMMUTABLE: Set at creation
    container_metadata: Optional[ContainerMetadata] = Field(
        None, description="The metadata of the container image"
    )  # IMMUTABLE: Analysis-determined
    bazel_metadata: Optional[BazelMetadata] = Field(
        None, description="The metadata of the bazel target"
    )  # IMMUTABLE: Analysis-determined
    code_owners: Optional[CodeOwnerData] = Field(
        None, description="Code owner data for the package"
    )  # IMMUTABLE: Analysis-determined
    call_graph_available: Optional[bool] = Field(
        None,
        description="True if call graph was successfully created by latest scan",
    )  # MUTABLE: Can be updated
    internal_reference_key: Optional[str] = Field(
        None,
        description="Unique key for package generated by Endor Labs for lookups",
    )  # IMMUTABLE: System-generated
    precomputed_call_graph_state: Optional[PrecomputedState] = Field(
        None, description="The state of the precomputed callgraph"
    )  # IMMUTABLE: System-managed

    @field_validator("ecosystem", mode="before")
    @classmethod
    def validate_ecosystem(cls, v):
        """Handle unknown ecosystem values gracefully."""
        if isinstance(v, str):
            try:
                return Ecosystem(v)
            except ValueError:
                logger.warning(f"Unknown Ecosystem value: {v}. Using as-is.")
                return v
        return v

    @field_validator("language", mode="before")
    @classmethod
    def validate_language(cls, v):
        """Handle unknown language values gracefully."""
        if isinstance(v, str):
            try:
                return Language(v)
            except ValueError:
                logger.warning(f"Unknown Language value: {v}. Using as-is.")
                return v
        return v


class PackageVersion(BaseResource):
    """PackageVersion resource model extending BaseResource."""

    # PackageVersion-specific fields (universal fields inherited from BaseResource)
    spec: PackageVersionSpec = Field(..., description="PackageVersion specification")  # type: ignore
    # Conditional attributes from Resource Guide example
    context: Optional[dict] = Field(
        None, description="Contextual information", alias="context"
    )
    processing_status: Optional[dict] = Field(
        None, description="Processing status information", alias="processing_status"
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data):
        # Convert spec to PackageVersionSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = PackageVersionSpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "project_uuid",
                "source_code_reference",
                "release_timestamp",
                "unresolved_dependencies",
                "resolved_dependencies",
                "resolution_errors",
                "ecosystem",
                "package_name",
                "language",
                "relative_path",
                "container_metadata",
                "bazel_metadata",
                "code_owners",
                "call_graph_available",
                "internal_reference_key",
                "precomputed_call_graph_state",
            }
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v


class UpdatePackageVersionPayload(BaseModel):
    """Payload for updating PackageVersion resources."""

    meta: Optional[dict] = None
    spec: Optional[PackageVersionSpec] = None
    update_mask: Optional[List[str]] = None


def _get_package_version_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for PackageVersion."""
    return BaseResourceOperations(client, "package-versions", PackageVersion)


def list_package_versions(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
    **kwargs,
) -> List[PackageVersion]:
    """List package versions with advanced filtering and pagination."""
    ops = _get_package_version_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)  # type: ignore


def get_package_version(
    client: APIClient, tenant_meta_namespace: str, package_version_uuid: str
) -> Optional[PackageVersion]:
    """Get specific package version by UUID."""
    ops = _get_package_version_ops(client)
    return ops.get(tenant_meta_namespace, package_version_uuid)  # type: ignore


def create_package_version(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: "CreatePackageVersionPayload",
) -> Optional[PackageVersion]:
    """Create a new package version."""
    ops = _get_package_version_ops(client)
    return ops.create(tenant_meta_namespace, payload)  # type: ignore


def update_package_version(
    client: APIClient,
    tenant_meta_namespace: str,
    package_version_uuid: str,
    payload: UpdatePackageVersionPayload,
    update_mask: Optional[List[str]] = None,
) -> Optional[PackageVersion]:
    """Update package version using base class operations."""
    ops = _get_package_version_ops(client)
    return ops.update(tenant_meta_namespace, package_version_uuid, payload, update_mask)  # type: ignore


def delete_package_version(
    client: APIClient, tenant_meta_namespace: str, package_version_uuid: str
) -> bool:
    """Delete a package version by UUID."""
    ops = _get_package_version_ops(client)
    return ops.delete(tenant_meta_namespace, package_version_uuid)  # type: ignore


# Payload models for create and update operations
class CreatePackageVersionPayload(BaseModel):
    """Payload for creating a package version."""

    meta: "PackageVersionMetaCreate" = Field(
        ..., description="PackageVersion metadata for creation"
    )
    spec: PackageVersionSpec = Field(..., description="PackageVersion specification")


class PackageVersionMetaCreate(BaseModel):
    """PackageVersion metadata for creation."""

    name: str = Field(..., description="PackageVersion name")
    description: Optional[str] = Field(None, description="PackageVersion description")


class PackageVersionMetaUpdate(BaseModel):
    """PackageVersion metadata for update."""

    description: Optional[str] = Field(None, description="PackageVersion description")
