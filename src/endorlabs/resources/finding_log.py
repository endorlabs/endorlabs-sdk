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

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseResourceOperations,
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

if TYPE_CHECKING:
    from ..api_client import APIClient
    from ..types import ListParameters

logger = logging.getLogger(__name__)


class FindingLogOperation(FlexibleEnum):
    """Finding log operation enumeration."""

    UNSPECIFIED = "OPERATION_UNSPECIFIED"
    READ = "OPERATION_READ"
    UPDATE = "OPERATION_UPDATE"


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
                logger.warning(f"Unknown FindingLogOperation value: {v}. Using as-is.")
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
                logger.warning(f"Unknown AnalysisMethod value: {v}. Using as-is.")
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
                logger.warning(f"Unknown FindingLevel value: {v}. Using as-is.")
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
                logger.warning(f"Unknown Ecosystem value: {v}. Using as-is.")
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
                            f"Unknown FindingTags value: {tag}. Using as-is."
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
                            f"Unknown FindingCategory value: {category}. Using as-is."
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

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Override BaseSpec drift detection to skip typed nested model fields."""
        # Skip drift detection for typed nested models
        # (they handle their own validation)
        typed_model_fields = {
            "snooze",  # DismissParams
        }
        if (
            info.field_name
            and isinstance(v, dict)
            and info.field_name not in typed_model_fields
        ):
            # Call parent validator for non-typed-model fields
            return super().detect_schema_drift(v, info)
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

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "finding_uuid",
                "finding_parent_kind",
                "finding_parent_uuid",
                "operation",
                "introduced_at",
                "resolved_at",
                "days_unresolved",
                "ecosystem",
                "target_uuid",
                "target_dependency_package_name",
                "method",
                "level",
                "finding_tags",
                "finding_categories",
                "approximation",
                "finding_parent_name",
                "snooze",
            }
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v


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


def _get_finding_log_ops(
    client: APIClient,
) -> BaseResourceOperations[FindingLog]:
    """Get BaseResourceOperations instance for finding logs."""
    return BaseResourceOperations(client, "finding-logs", FindingLog)


def list_finding_logs(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[FindingLog]:
    """List finding logs in a namespace.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name (e.g., 'tenant.namespace')
        list_params: Optional list parameters for filtering, pagination, etc.
        max_pages: Optional maximum number of pages to fetch.
            If None and in test environment, defaults to 10 pages max.
            If None in production, fetches all pages.
        **kwargs: Passed through to list implementation (e.g. filter, page_size).

    Returns:
        List of FindingLog objects

    """
    ops = _get_finding_log_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def list_finding_logs_iter(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[FindingLog]:
    """Iterate over finding logs without materializing the full list."""
    ops = _get_finding_log_ops(client)
    return ops.list_iter(tenant_meta_namespace, list_params, max_pages, **kwargs)


def get_finding_log(
    client: APIClient, tenant_meta_namespace: str, finding_log_uuid: str
) -> FindingLog:
    """Get a specific finding log by UUID.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        finding_log_uuid: UUID of the finding log to retrieve

    Returns:
        FindingLog object

    Raises:
        NotFoundError: If finding log doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    ops = _get_finding_log_ops(client)
    return ops.get(tenant_meta_namespace, finding_log_uuid)


def create_finding_log(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateFindingLogPayload,
) -> FindingLog:
    """Create a new finding log with pre-validation and typed errors.

    Note: FindingLogs are typically generated automatically when findings are
    modified. This function is provided for completeness but is rarely used
    by end users.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        payload: FindingLog creation payload

    Returns:
        Created FindingLog object

    Raises:
        ValidationError: If payload is invalid
        NotFoundError: If namespace doesn't exist
        PermissionDeniedError: If user lacks permission
        ConflictError: If finding log already exists
        ServerError: If server error occurs

    """
    ops = _get_finding_log_ops(client)
    return ops.create(tenant_meta_namespace, payload)


def delete_finding_log(
    client: APIClient, tenant_meta_namespace: str, finding_log_uuid: str
) -> bool:
    """Delete a finding log.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        finding_log_uuid: UUID of the finding log to delete

    Returns:
        True if deletion was successful, False otherwise

    """
    ops = _get_finding_log_ops(client)
    return ops.delete(tenant_meta_namespace, finding_log_uuid)
