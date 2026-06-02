"""PackageLicense resource module for Endor Labs API.

This module provides CRUD operations for PackageLicense resources following the
established patterns from the base class implementation.

IMPORTANT: All PackageLicense operations are hardcoded to use the "oss" namespace.
The tenant_meta_namespace parameter in all functions is kept for API compatibility
but is ignored - all operations always use the "oss" namespace regardless of the
parameter value passed.
"""

from __future__ import annotations

from typing import Any, override

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
)
from ..utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)


class PackageLicenseInfoLicenseInfoMapping(BaseModel):
    """License info mapping information."""

    mapping_info: str | None = Field(None, description="License mapping information")

    model_config = ConfigDict(extra="allow")


class PackageLicenseInfo(BaseModel):
    """Package license information model."""

    license_description: str = Field(
        ...,
        description=(
            "Raw license description as found, for example in package managers. "
            "It is free form text that may not contain a valid SPDX ID."
        ),
    )
    spdx_id: str | None = Field(None, description="Normalized SPDX id if known.")
    spdx_expr: str | None = Field(None, description="SPDX expression for the license.")
    mapping_info: PackageLicenseInfoLicenseInfoMapping | None = Field(
        None, description="Additional context about the raw license description."
    )
    type: str | None = Field(
        None,
        description="License classification (based on licenseclassifier by Google).",
    )
    url: str | None = Field(
        None, description="The URL that points to the license description."
    )
    file_name: str | None = Field(
        None, description="The name of the file where the license was found."
    )
    file_location: int | None = Field(
        None,
        description="The line in the file where the license text begins.",
    )
    matched_text: str | None = Field(
        None, description="The license text that was matched."
    )
    notices_file: bool | None = Field(
        None,
        description="True if it is a notices file identified by name.",
    )
    confidence: float | None = Field(
        None, description="The confidence in the license match."
    )
    llm: str | None = Field(
        None,
        description=(
            "The LLM used to identify the license, if applicable. "
            "If no LLM was used, then this will be empty."
        ),
    )
    copyrights: list[str] | None = Field(
        None, description="Copyrights within the license text."
    )
    hash: str | None = Field(
        None,
        description="Hash should only be set if matched_text is empty.",
    )
    additional_files: dict[str, int] | None = Field(
        None,
        description=(
            "Other files that contain the same license, mapped to line number."
        ),
    )

    model_config = ConfigDict(extra="allow")

    @field_validator("mapping_info", mode="before")
    @classmethod
    def validate_mapping_info(cls, v: Any) -> Any:
        """Handle mapping_info validation."""
        if isinstance(v, dict):
            return PackageLicenseInfoLicenseInfoMapping(**v)
        return v


class PackageLicenseMeta(BaseMeta):
    """PackageLicense metadata extending BaseMeta."""

    # PackageLicense-specific fields only (universal fields inherited from BaseMeta)
    pass


class PackageLicenseSpec(BaseSpec):
    """PackageLicense specification extending BaseSpec.

    Field Mutability Guide:
    ======================

    IMMUTABLE FIELDS (cannot be updated after creation):
    - code_licenses: Discovered licenses in source code (set at creation)
    - package_manager_licenses: Licenses from package manager (set at creation)
    - copyrights: Copyright notices per file (set at creation)
    - declared_code_licenses: Declared licenses in source code (set at creation)
    - license_text: Map of hash to license text (set at creation)
    - all_licenses: All licenses found by Endor Labs (set at creation)
    - project_uuid: Project assignment (set at creation)

    MUTABLE FIELDS (can be updated via API):
    - None (PackageLicense is typically immutable after creation)
    """

    code_licenses: list[PackageLicenseInfo] | None = Field(
        None, description="The discovered licenses found in the source code."
    )  # IMMUTABLE: Set at creation
    package_manager_licenses: list[PackageLicenseInfo] | None = Field(
        None, description="The licenses from the package manager."
    )  # IMMUTABLE: Set at creation
    copyrights: dict[str, str] | None = Field(
        None,
        description=(
            "The map of copyright notices per file name found in source files. "
            "The key is the file name and the value is the copyright notice "
            "texts combined together into a single string."
        ),
    )  # IMMUTABLE: Set at creation
    declared_code_licenses: list[PackageLicenseInfo] | None = Field(
        None, description="The declared licenses found in the source code."
    )  # IMMUTABLE: Set at creation
    license_text: dict[str, str] | None = Field(
        None, description="Map of sha256 to license text."
    )  # IMMUTABLE: Set at creation
    all_licenses: list[PackageLicenseInfo] | None = Field(
        None, description="All the licenses found by Endor Labs."
    )  # IMMUTABLE: Set at creation
    project_uuid: str | None = Field(
        None,
        description="UUID of the project that the package license relates to.",
    )  # IMMUTABLE: Set at creation

    @field_validator(
        "code_licenses",
        "package_manager_licenses",
        "declared_code_licenses",
        "all_licenses",
        mode="before",
    )
    @classmethod
    def validate_license_lists(cls, v: Any) -> Any:
        """Handle license list validation."""
        if isinstance(v, list):
            return [
                PackageLicenseInfo(**item) if isinstance(item, dict) else item
                for item in v
            ]
        return v


class PackageLicense(BaseResource):
    """PackageLicense resource model extending BaseResource.

    IMPORTANT: All PackageLicense operations are hardcoded to use the "oss" namespace.
    This resource always queries the OSS (Open Source Software) namespace regardless of
    the namespace parameter passed to the operation functions.
    """

    # PackageLicense-specific fields (universal fields inherited from BaseResource)
    spec: PackageLicenseSpec = Field(..., description="PackageLicense specification")  # type: ignore

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data: Any) -> None:
        # Convert spec to PackageLicenseSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = PackageLicenseSpec(**data["spec"])
        super().__init__(**data)

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "code_licenses",
                "package_manager_licenses",
                "copyrights",
                "declared_code_licenses",
                "license_text",
                "all_licenses",
                "project_uuid",
            }
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
        """Get list of mutable fields for PackageLicense."""
        return ["meta.name", "meta.description", "meta.tags", "spec"]


# Payload models for create and update operations
class CreatePackageLicensePayload(BaseModel):
    """Payload for creating a package license."""

    meta: PackageLicenseMetaCreate = Field(
        ..., description="PackageLicense metadata for creation"
    )
    spec: PackageLicenseSpec = Field(..., description="PackageLicense specification")


def build_create_payload(**kwargs: Any) -> CreatePackageLicensePayload:
    """Build CreatePackageLicensePayload from kwargs (decoupled create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreatePackageLicensePayload, kwargs, attr_name="PackageLicense"
    )


class UpdatePackageLicensePayload(BaseModel):
    """Payload for updating a package license."""

    meta: PackageLicenseMetaUpdate | None = Field(
        None, description="PackageLicense metadata for update"
    )
    spec: PackageLicenseSpec | None = Field(
        None, description="PackageLicense specification for update"
    )


class PackageLicenseMetaCreate(BaseModel):
    """PackageLicense metadata for creation."""

    name: str = Field(..., description="PackageLicense name")
    description: str | None = Field(None, description="PackageLicense description")


class PackageLicenseMetaUpdate(BaseModel):
    """PackageLicense metadata for update."""

    description: str | None = Field(None, description="PackageLicense description")
