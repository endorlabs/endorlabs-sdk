"""PackageVersion resource module for Endor Labs API.

This module provides CRUD operations for PackageVersion resources following the
established patterns from the base class implementation.

API OPERATIONS SUPPORTED:
- GET: List package versions, Get package version by UUID

API LIMITATIONS:
- CREATE: Not supported by API (package versions are discovered by scans)
- UPDATE: Not supported by API (returns 501 Method Not Allowed)
- DELETE: Not supported by API (package versions are immutable)

Note: Package versions are automatically discovered during security scans and cannot
be manually created, updated, or deleted. The API returns 501 Not Allowed for
PATCH operations on package versions.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime
from typing import TYPE_CHECKING, Any, override

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseResourceOperations,
    BaseSpec,
    FlexibleEnum,
)
from ..utils.model_validation import parse_update_mask

if TYPE_CHECKING:
    from ..types import ListParameters

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


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


class Language(FlexibleEnum):
    """Language enumeration."""

    UNSPECIFIED = "LANGUAGE_UNSPECIFIED"
    C = "LANGUAGE_C"
    CPP = "LANGUAGE_CPP"
    CSHARP = "LANGUAGE_CSHARP"
    GO = "LANGUAGE_GO"
    JAVA = "LANGUAGE_JAVA"
    JS = "LANGUAGE_JS"
    KOTLIN = "LANGUAGE_KOTLIN"
    OBJECTIVEC = "LANGUAGE_OBJECTIVEC"
    PHP = "LANGUAGE_PHP"
    PYTHON = "LANGUAGE_PYTHON"
    RUBY = "LANGUAGE_RUBY"
    RUST = "LANGUAGE_RUST"
    SCALA = "LANGUAGE_SCALA"
    SWIFT = "LANGUAGE_SWIFT"
    SWIFTURL = "LANGUAGE_SWIFTURL"
    TYPESCRIPT = "LANGUAGE_TYPESCRIPT"


class VersionInfo(BaseModel):
    """Version information with ref, sha, and metadata."""

    ref: str = Field(..., description="Reference (branch, tag, or commit)")
    sha: str | None = Field(None, description="Commit SHA")
    metadata: dict[str, Any] | None = Field(None, description="Version metadata")


class PackageVersionSourceCodeReference(BaseModel):
    """Source code reference for package version."""

    model_config = ConfigDict(extra="allow")  # Allow flat structure from API

    version: VersionInfo | None = Field(
        None, description="Version information (ref, sha, metadata)"
    )
    ref: str | None = Field(
        None, description="Reference (branch, tag, or commit) - legacy field"
    )
    sha: str | None = Field(None, description="Commit SHA - legacy field")
    http_clone_url: str | None = Field(None, description="HTTP clone URL")
    platform_source: str | None = Field(None, description="Platform source")
    repository_uuid: str | None = Field(None, description="Repository UUID")


class PackageVersionDependency(BaseModel):
    """Package version dependency."""

    name: str = Field(..., description="Dependency name (may include version)")
    version: str | None = Field(
        None, description="Dependency version (may be in name field)"
    )
    ecosystem: Ecosystem | None = Field(None, description="Dependency ecosystem")

    model_config = ConfigDict(extra="allow")  # Allow ecosystem-specific fields


class Bom(BaseModel):
    """Bill of Materials for resolved dependencies."""

    resolution_timestamp: datetime | None = Field(
        None, description="Resolution timestamp"
    )
    dependency_graph: dict[str, Any] | None = Field(
        None, description="Dependency graph structure"
    )
    dependencies: list[PackageVersionDependency | dict[str, Any]] | None = Field(
        None, description="Resolved dependencies (can be objects or dicts)"
    )
    dependency_files: list[str] | None = Field(
        None, description="Dependency file paths"
    )

    model_config = ConfigDict(extra="allow")  # Allow additional fields


class PackageVersionResolutionErrors(BaseModel):
    """Resolution errors for package version."""

    errors: list[str] | None = Field(None, description="List of resolution errors")
    unresolved: dict[str, Any] | None = Field(
        None, description="Unresolved dependency errors"
    )
    resolved: dict[str, Any] | None = Field(
        None, description="Resolved dependency errors"
    )
    call_graph: dict[str, Any] | None = Field(None, description="Call graph errors")

    model_config = ConfigDict(extra="allow")  # Allow additional fields


class ContainerMetadata(BaseModel):
    """Container metadata."""

    image_name: str = Field(..., description="Container image name")
    tag: str | None = Field(None, description="Container tag")
    digest: str | None = Field(None, description="Container digest")


class BazelMetadata(BaseModel):
    """Bazel metadata."""

    target: str = Field(..., description="Bazel target")
    package: str | None = Field(None, description="Bazel package")


class CodeOwnerData(BaseModel):
    """Code owner data."""

    owners: list[str] = Field(..., description="List of code owners")
    paths: list[str] | None = Field(None, description="List of owned paths")
    labels: list[str] | None = Field(None, description="List of labels")

    model_config = ConfigDict(extra="allow")  # Allow additional fields


class PrecomputedState(BaseModel):
    """Precomputed state for call graph."""

    state: str = Field(..., description="Precomputed state")
    timestamp: datetime | None = Field(None, description="State timestamp")


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
    source_code_reference: PackageVersionSourceCodeReference | None = Field(
        None,
        description="Ref info of source code repository from which package was created",
    )  # IMMUTABLE: Set at creation
    release_timestamp: datetime | None = Field(
        None,
        description="Release timestamp when this package version was released",
    )  # IMMUTABLE: Set at creation
    unresolved_dependencies: list[dict[str, Any]] | None = Field(
        None,
        description=(
            "Exact dependency declarations in package manager descriptor file. "
            "Each item is a dict with ecosystem-specific keys (e.g., 'pypi', 'npm')"
        ),
    )  # MUTABLE: Can be updated
    resolved_dependencies: Bom | dict[str, Any] | None = Field(
        None, description="A graph of resolved dependencies (Bom or dict)"
    )  # MUTABLE: Can be updated
    resolution_errors: PackageVersionResolutionErrors | None = Field(
        None, description="Captures any errors during dependency resolution"
    )  # MUTABLE: Can be updated
    ecosystem: Ecosystem | None = Field(
        None, description="Dependency ecosystem"
    )  # IMMUTABLE: Analysis-determined
    package_name: str | None = Field(
        None, description="The name of the package of this package version"
    )  # IMMUTABLE: Analysis-determined
    language: Language | None = Field(
        None, description="Language of the package_version"
    )  # IMMUTABLE: Analysis-determined
    relative_path: str | None = Field(
        None,
        description="Relative path of package from discovery point to workspace root",
    )  # IMMUTABLE: Set at creation
    container_metadata: ContainerMetadata | None = Field(
        None, description="The metadata of the container image"
    )  # IMMUTABLE: Analysis-determined
    bazel_metadata: BazelMetadata | None = Field(
        None, description="The metadata of the bazel target"
    )  # IMMUTABLE: Analysis-determined
    code_owners: CodeOwnerData | None = Field(
        None, description="Code owner data for the package"
    )  # IMMUTABLE: Analysis-determined
    call_graph_available: bool | None = Field(
        None,
        description="True if call graph was successfully created by latest scan",
    )  # MUTABLE: Can be updated
    internal_reference_key: str | None = Field(
        None,
        description="Unique key for package generated by Endor Labs for lookups",
    )  # IMMUTABLE: System-generated
    precomputed_call_graph_state: PrecomputedState | str | dict[str, Any] | None = (
        Field(
            None,
            description=(
                "The state of the precomputed callgraph. "
                "Can be PrecomputedState object, string enum, or dict"
            ),
        )
    )  # IMMUTABLE: System-managed

    @field_validator("ecosystem", mode="before")
    @classmethod
    def validate_ecosystem(cls, v: Any) -> Any:
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
    def validate_language(cls, v: Any) -> Any:
        """Handle unknown language values gracefully."""
        if isinstance(v, str):
            try:
                return Language(v)
            except ValueError:
                logger.warning(f"Unknown Language value: {v}. Using as-is.")
                return v
        return v

    @field_validator("source_code_reference", mode="before")
    @classmethod
    def validate_source_code_reference(cls, v: Any) -> Any:
        """Handle source_code_reference with nested version structure."""
        if isinstance(v, dict) and "version" in v and isinstance(v["version"], dict):
            version_info = v["version"]
            # Keep the nested version but also set ref/sha at top level if missing
            if "ref" not in v and "ref" in version_info:
                v["ref"] = version_info["ref"]
            if "sha" not in v and "sha" in version_info:
                v["sha"] = version_info.get("sha")
        return v

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Override BaseSpec drift detection to skip typed model fields."""
        # Skip drift detection for typed nested models
        # (they handle their own validation)
        typed_model_fields = {
            "source_code_reference",  # PackageVersionSourceCodeReference
            "resolved_dependencies",  # Bom or dict
            "resolution_errors",  # PackageVersionResolutionErrors
            "code_owners",  # CodeOwnerData
            "container_metadata",  # ContainerMetadata
            "bazel_metadata",  # BazelMetadata
        }
        if (
            info.field_name
            and isinstance(v, dict)
            and info.field_name not in typed_model_fields
        ):
            # Call parent validator for non-typed-model fields
            return super().detect_schema_drift(v, info)
        return v


class PackageVersion(BaseResource):
    """PackageVersion resource model extending BaseResource.

    OPERATION SUPPORT:
    ==================
    ✅ GET: List package versions, Get by UUID
    ❌ CREATE: Not supported (discovered by scans)
    ❌ UPDATE: Not supported (returns 501 Method Not Allowed)
    ❌ DELETE: Not supported (package versions are immutable)

    FIELD MUTABILITY (per OpenAPI spec):
    =====================================
    Note: UpdatePackageVersion endpoint exists in API spec but returns
    501 Method Not Allowed.

    IMMUTABLE FIELDS (readOnly: true in API spec):
    - uuid: Unique identifier (readOnly: true in UpdatePackageVersion request body)
    - meta.create_time, meta.update_time, meta.upsert_time: Timestamps
      (readOnly: true in v1Meta)
    - meta.kind, meta.version: Resource metadata (readOnly: true in v1Meta)
    - meta.created_by, meta.updated_by: Audit fields (readOnly: true in v1Meta)
    - meta.references, meta.index_data: System-managed fields (readOnly: true in v1Meta)
    - spec.ecosystem: Package ecosystem (readOnly: true in v1PackageVersionSpec)
    - spec.package_name: Package name (readOnly: true in v1PackageVersionSpec)
    - spec.internal_reference_key: Internal reference key
      (readOnly: true in v1PackageVersionSpec)
    - tenant_meta.namespace: Namespace assignment

    MUTABLE FIELDS (NOT readOnly in API spec, but Update returns 501):
    - meta.name, meta.description, meta.tags: Metadata
    - spec.project_uuid: Project assignment
    - spec.source_code_reference: Source code reference
    - spec.release_timestamp: Release timestamp
    - spec.unresolved_dependencies: Dependency declarations
    - spec.resolved_dependencies: Resolved dependency graph
    - spec.resolution_errors: Resolution errors
    - spec.language: Programming language
    - spec.relative_path: Relative path
    - spec.container_metadata: Container metadata
    - spec.bazel_metadata: Bazel metadata
    - spec.code_owners: Code owner data
    - spec.call_graph_available: Call graph availability
    - spec.precomputed_call_graph_state: Precomputed call graph state
    - processing_status.*: All processing status fields
    - context.*: Context fields

    Note: Package versions are automatically discovered during security scans and
    cannot be manually created, updated, or deleted. PATCH operations return 501.
    """

    # PackageVersion-specific fields (universal fields inherited from BaseResource)
    spec: PackageVersionSpec = Field(..., description="PackageVersion specification")  # type: ignore
    # Conditional attributes from Resource Guide example
    context: dict[str, Any] | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Contextual information", alias="context"
    )
    processing_status: dict[str, Any] | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Processing status information", alias="processing_status"
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data: Any) -> None:
        # Convert spec to PackageVersionSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = PackageVersionSpec(**data["spec"])
        super().__init__(**data)

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
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

    @override
    @classmethod
    def get_mutable_fields_cls(cls) -> list[str]:
        """Get list of mutable fields for PackageVersion."""
        return ["meta.name", "meta.description", "meta.tags", "spec"]

    @override
    @classmethod
    def get_immutable_fields_cls(cls) -> list[str]:
        """Get list of immutable fields for PackageVersion."""
        return [
            "uuid",
            "meta.create_time",
            "meta.created_by",
            "meta.update_time",
            "meta.updated_by",
            "meta.upsert_time",
            "meta.kind",
            "meta.version",
            "meta.references",
            "meta.index_data",
            "tenant_meta.namespace",
            "spec.ecosystem",
            "spec.package_name",
            "spec.internal_reference_key",
        ]


class UpdatePackageVersionPayload(BaseModel):
    """Payload for updating PackageVersion resources."""

    meta: dict[str, Any] | None = None
    spec: PackageVersionSpec | None = None
    update_mask: list[str] | None = None


def _get_package_version_ops(
    client: APIClient,
) -> BaseResourceOperations[PackageVersion]:
    """Get BaseResourceOperations instance for PackageVersion."""
    return BaseResourceOperations(client, "package-versions", PackageVersion)


def list_package_versions(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[PackageVersion]:
    """List package versions with advanced filtering and pagination."""
    ops = _get_package_version_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def list_package_versions_iter(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[PackageVersion]:
    """Iterate over package versions without materializing the full list."""
    ops = _get_package_version_ops(client)
    return ops.list_iter(tenant_meta_namespace, list_params, max_pages, **kwargs)


def get_package_version(
    client: APIClient, tenant_meta_namespace: str, package_version_uuid: str
) -> PackageVersion:
    """Get specific package version by UUID.

    Raises:
        NotFoundError: If package version doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    ops = _get_package_version_ops(client)
    return ops.get(tenant_meta_namespace, package_version_uuid)


def create_package_version(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreatePackageVersionPayload,
) -> PackageVersion:
    """Create a new package version with pre-validation and typed errors.

    Raises:
        ValidationError: If payload is invalid
        NotFoundError: If namespace doesn't exist
        PermissionDeniedError: If user lacks permission
        ConflictError: If package version already exists
        ServerError: If server error occurs

    """
    ops = _get_package_version_ops(client)
    return ops.create(tenant_meta_namespace, payload)


def update_package_version(
    client: APIClient,
    tenant_meta_namespace: str,
    package_version_uuid: str,
    payload: UpdatePackageVersionPayload,
    update_mask: str,
) -> PackageVersion | None:
    """Update package version using base class operations.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        package_version_uuid: UUID of the package version to update
        payload: PackageVersion update payload
        update_mask: Comma-separated list of fields to update (required), e.g.
            "meta.tags,meta.description". Missing or empty raises ValidationError.

    Returns:
        Updated PackageVersion object

    Raises:
        ValidationError: If payload is invalid or update_mask is missing/empty
        NotFoundError: If package version doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    from ..exceptions import ValidationError as EndorValidationError

    if not (update_mask and update_mask.strip()):
        raise EndorValidationError(
            message=(
                "Package version update requires an update_mask "
                "(e.g. 'meta.description', 'meta.tags')."
            ),
            operation="update",
            namespace=tenant_meta_namespace,
            resource_uuid=package_version_uuid,
        )
    # Convert update_mask from string to List[str] for base class
    update_mask_list = parse_update_mask(update_mask)
    ops = _get_package_version_ops(client)
    return ops.update(
        tenant_meta_namespace, package_version_uuid, payload, update_mask_list
    )


def delete_package_version(
    client: APIClient, tenant_meta_namespace: str, package_version_uuid: str
) -> bool:
    """Delete a package version by UUID."""
    ops = _get_package_version_ops(client)
    return ops.delete(tenant_meta_namespace, package_version_uuid)


# Payload models for create and update operations
class CreatePackageVersionPayload(BaseModel):
    """Payload for creating a package version."""

    meta: PackageVersionMetaCreate = Field(
        ..., description="PackageVersion metadata for creation"
    )
    spec: PackageVersionSpec = Field(..., description="PackageVersion specification")


def build_create_payload(**kwargs: Any) -> CreatePackageVersionPayload:
    """Build CreatePackageVersionPayload from kwargs (decoupled create)."""
    return CreatePackageVersionPayload(**kwargs)


class PackageVersionMetaCreate(BaseModel):
    """PackageVersion metadata for creation."""

    name: str = Field(..., description="PackageVersion name")
    description: str | None = Field(None, description="PackageVersion description")


class PackageVersionMetaUpdate(BaseModel):
    """PackageVersion metadata for update."""

    description: str | None = Field(None, description="PackageVersion description")
