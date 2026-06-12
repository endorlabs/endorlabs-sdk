"""FindingLog resource module for Endor Labs API.

This module provides CRUD operations for FindingLog resources following the established
patterns from the Finding, ScanResult, Policy, and Project resource implementations.

API OPERATIONS SUPPORTED:
- GET: List finding logs, Get finding log by UUID
- POST: Create finding log
- DELETE: Delete finding log

API USAGE NOTES:
- FindingLogs track the state of findings at the time they were created,
  updated, or deleted
- FindingLogs are automatically generated when findings are modified
- Can be manually created for audit purposes
- Useful for tracking finding history and snooze information
- For more information, see the FindingLogService REST API documentation
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..utils.logging_config import get_resource_logger
from .base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
    Context,
    FlexibleEnum,
)
from .finding import (
    AnalysisMethod,
    Ecosystem,
    FindingCategory,
    FindingLevel,
    FindingTags,
)

logger = get_resource_logger(__name__)


class FindingLogOperation(FlexibleEnum):
    """Finding log operation enumeration.

    Values per OpenAPI spec ``v1FindingLogSpecOperation``.
    """

    UNSPECIFIED = "OPERATION_UNSPECIFIED"
    CREATE = "OPERATION_CREATE"
    UPDATE = "OPERATION_UPDATE"
    DELETE = "OPERATION_DELETE"


class DismissParams(BaseModel):
    """Dismiss parameters for snooze/ignore functionality."""

    updated_by: str | None = Field(
        None, description="Username of the user who last updated the snooze or ignore"
    )
    update_time: str | None = Field(
        None,
        description="Timestamp of the last update",
        json_schema_extra={"format": "date-time"},
    )
    expiration_time: str | None = Field(
        None,
        description="Expiration time of the snooze or ignore",
        json_schema_extra={"format": "date-time"},
    )
    expire_if_fix_available: bool | None = Field(
        None,
        description=(
            "Set to true if the snooze or ignore should expire if a fix is available"
        ),
    )


class FindingLogMeta(BaseMeta):
    """Finding log metadata extending BaseMeta."""

    # FindingLog-specific fields (universal fields inherited from BaseMeta)
    pass  # No additional fields needed, all were universal


class FindingLogSpec(BaseSpec):
    """Finding log specification extending BaseSpec.

    Field Mutability Guide:
    ======================

    FIELD MUTABILITY (per OpenAPI spec):
    =====================================
    Note: FindingLogs are typically system-generated when findings are modified.
    Most fields are immutable and reflect the state of the finding at the time
    the log entry was created.

    IMMUTABLE FIELDS (read-only, system-generated):
    - finding_uuid: UUID of the finding (set at creation)
    - finding_parent_kind: Parent object resource kind (set at creation)
    - finding_parent_uuid: Parent object UUID (set at creation)
    - operation: Operation that triggered the log (set at creation)
    - introduced_at: Time finding was introduced (set at creation)
    - resolved_at: Time finding was resolved (set at creation)
    - days_unresolved: Days finding remained unresolved (calculated)
    - method: Analysis method used (set at creation)
    - level: Finding severity level (set at creation)
    - finding_tags: Finding tags at time of operation (set at creation)
    - finding_categories: Finding categories at time of operation (set at creation)
    - ecosystem: Ecosystem where finding was detected (set at creation)
    - target_uuid: DependencyMetadata UUID (set at creation)
    - target_dependency_package_name: Dependency package name (set at creation)
    - approximation: Whether finding is for approximate dependency (set at creation)
    - finding_parent_name: Parent object name (set at creation)
    - snooze: Snooze parameters (set at creation)

    MUTABLE FIELDS (if any):
    - None identified in practice (all fields are log entries)
    """

    # Required fields
    finding_uuid: str = Field(..., description="The UUID of the finding")
    finding_parent_kind: str = Field(
        ...,
        description="Finding parent object resource kind. For example, PackageVersion.",
    )
    finding_parent_uuid: str = Field(..., description="Finding parent object UUID")
    operation: FindingLogOperation = Field(
        ...,
        description="Operation that triggered the creation of this finding log",
    )
    introduced_at: str = Field(
        ...,
        description="Time the finding was introduced",
        json_schema_extra={"format": "date-time"},
    )
    method: AnalysisMethod = Field(
        ..., description="Method used to compute the finding"
    )
    level: FindingLevel = Field(..., description="Finding severity level")
    finding_tags: list[FindingTags] = Field(
        ...,
        description=(
            "List of tags, or attributes, that describe the scope of the finding "
            "and can be used to filter findings"
        ),
    )
    finding_categories: list[FindingCategory] = Field(
        ...,
        description=(
            "List of categories that capture the use case to which the finding fits"
        ),
    )

    # Optional fields
    resolved_at: str | None = Field(
        None,
        description="Time the finding was resolved",
        json_schema_extra={"format": "date-time"},
    )
    days_unresolved: int | None = Field(
        None, description="Number of days that this finding remained unresolved"
    )
    ecosystem: Ecosystem | None = Field(
        None, description="Ecosystem where the finding was detected"
    )
    target_uuid: str | None = Field(
        None,
        description="The UUID of the DependencyMetadata object for the dependency",
    )
    target_dependency_package_name: str | None = Field(
        None,
        description=(
            "Fully qualified name of the dependency. For example, "
            "eco://package@version."
        ),
    )
    approximation: bool | None = Field(
        None,
        description=(
            "True if this finding is for an approximate dependency "
            "based on the unresolved package dependencies"
        ),
    )
    finding_parent_name: str | None = Field(
        None, description="finding_parent_name is the name of the parent object"
    )
    snooze: DismissParams | None = Field(None, description="Snooze params")

    @field_validator("operation", mode="before")
    @classmethod
    def validate_operation(cls, v: Any) -> Any:
        """Handle unknown operation values gracefully."""
        if isinstance(v, str):
            try:
                return FindingLogOperation(v)
            except ValueError:
                logger.warning("Unknown FindingLogOperation value: %s. Using as-is.", v)
                return v
        return v

    @field_validator("method", mode="before")
    @classmethod
    def validate_method(cls, v: Any) -> Any:
        """Handle unknown method values gracefully."""
        if isinstance(v, str):
            try:
                return AnalysisMethod(v)
            except ValueError:
                logger.warning("Unknown AnalysisMethod value: %s. Using as-is.", v)
                return v
        return v

    @field_validator("level", mode="before")
    @classmethod
    def validate_level(cls, v: Any) -> Any:
        """Handle unknown level values gracefully."""
        if isinstance(v, str):
            try:
                return FindingLevel(v)
            except ValueError:
                logger.warning("Unknown FindingLevel value: %s. Using as-is.", v)
                return v
        return v

    @field_validator("ecosystem", mode="before")
    @classmethod
    def validate_ecosystem(cls, v: Any) -> Any:
        """Handle unknown ecosystem values gracefully."""
        if isinstance(v, str):
            try:
                return Ecosystem(v)
            except ValueError:
                logger.warning("Unknown Ecosystem value: %s. Using as-is.", v)
                return v
        return v

    @field_validator("finding_tags", mode="before")
    @classmethod
    def validate_finding_tags(cls, v: Any) -> Any:
        """Handle finding tags validation."""
        if isinstance(v, list):
            validated_tags = []
            for tag in v:
                if isinstance(tag, str):
                    try:
                        validated_tags.append(FindingTags(tag))
                    except ValueError:
                        logger.warning(
                            "Unknown FindingTags value: %s. Using as-is.",
                            tag,
                        )
                        validated_tags.append(tag)
                else:
                    validated_tags.append(tag)
            return validated_tags
        return v

    @field_validator("finding_categories", mode="before")
    @classmethod
    def validate_finding_categories(cls, v: Any) -> Any:
        """Handle finding categories validation."""
        if isinstance(v, list):
            validated_categories = []
            for category in v:
                if isinstance(category, str):
                    try:
                        validated_categories.append(FindingCategory(category))
                    except ValueError:
                        logger.warning(
                            "Unknown FindingCategory value: %s. Using as-is.",
                            category,
                        )
                        validated_categories.append(category)
                else:
                    validated_categories.append(category)
            return validated_categories
        return v

    @field_validator("snooze", mode="before")
    @classmethod
    def validate_snooze(cls, v: Any) -> Any:
        """Handle snooze as dict or DismissParams model."""
        if v is None:
            return None
        if isinstance(v, DismissParams):
            return v
        if isinstance(v, dict):
            return DismissParams(**v)
        return v


class FindingLog(BaseResource):
    """An Endor Labs FindingLog entity extending BaseResource.

    FindingLog-specific fields (universal fields inherited from BaseResource).

    OPERATION SUPPORT:
    ==================
    ✅ GET: List finding logs, Get by UUID
    ✅ POST: Create finding log
    ✅ DELETE: Delete finding log
    ❌ PATCH: Not supported (finding logs are immutable audit records)

    FIELD MUTABILITY:
    =================
    IMMUTABLE FIELDS (read-only, system-generated):
    - uuid: Unique identifier
    - meta.name: Finding log name (set at creation)
    - spec.*: All spec fields are immutable (audit record)
    - tenant_meta.namespace: Namespace assignment

    Note: FindingLogs are audit records that track the state of findings
    at the time they were created, updated, or deleted. They cannot be
    modified after creation.
    """

    # FindingLog-specific fields (universal fields inherited from BaseResource)
    spec: FindingLogSpec = Field(..., description="Finding log specification")  # type: ignore
    context: Context = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        ..., description="Context information for the finding log", alias="context"
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data: Any) -> None:
        # Convert spec to FindingLogSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = FindingLogSpec(**data["spec"])
        super().__init__(**data)


class FindingLogMetaCreate(BaseModel):
    """Metadata for creating a FindingLog."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="The name of the finding log"
    )
    description: str | None = Field(None, description="Description of the finding log")


class FindingLogSpecCreate(BaseModel):
    """Specification for creating a FindingLog."""

    finding_uuid: str = Field(..., description="The UUID of the finding")
    finding_parent_kind: str = Field(
        ...,
        description="Finding parent object resource kind. For example, PackageVersion.",
    )
    finding_parent_uuid: str = Field(..., description="Finding parent object UUID")
    operation: FindingLogOperation = Field(
        ...,
        description="Operation that triggered the creation of this finding log",
    )
    introduced_at: str = Field(
        ...,
        description="Time the finding was introduced",
        json_schema_extra={"format": "date-time"},
    )
    method: AnalysisMethod = Field(
        ..., description="Method used to compute the finding"
    )
    level: FindingLevel = Field(..., description="Finding severity level")
    finding_tags: list[FindingTags] = Field(
        ...,
        description=(
            "List of tags, or attributes, that describe the scope of the finding "
            "and can be used to filter findings"
        ),
    )
    finding_categories: list[FindingCategory] = Field(
        ...,
        description=(
            "List of categories that capture the use case to which the finding fits"
        ),
    )
    resolved_at: str | None = Field(
        None,
        description="Time the finding was resolved",
        json_schema_extra={"format": "date-time"},
    )
    days_unresolved: int | None = Field(
        None, description="Number of days that this finding remained unresolved"
    )
    ecosystem: Ecosystem | None = Field(
        None, description="Ecosystem where the finding was detected"
    )
    target_uuid: str | None = Field(
        None,
        description="The UUID of the DependencyMetadata object for the dependency",
    )
    target_dependency_package_name: str | None = Field(
        None,
        description=(
            "Fully qualified name of the dependency. For example, "
            "eco://package@version."
        ),
    )
    approximation: bool | None = Field(
        None,
        description=(
            "True if this finding is for an approximate dependency "
            "based on the unresolved package dependencies"
        ),
    )
    finding_parent_name: str | None = Field(
        None, description="finding_parent_name is the name of the parent object"
    )
    snooze: DismissParams | None = Field(None, description="Snooze params")


class CreateFindingLogPayload(BaseModel):
    """Payload for creating a new FindingLog."""

    meta: FindingLogMetaCreate
    spec: FindingLogSpecCreate
    context: Context


def build_create_payload(**kwargs: Any) -> CreateFindingLogPayload:
    """Build CreateFindingLogPayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateFindingLogPayload, kwargs, attr_name="FindingLog"
    )
