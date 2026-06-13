"""Base model classes for Endor Labs resources.

This module provides base classes that define the common patterns
used across all Endor Labs resource models.

CRUD operations live in ``endorlabs.operations.BaseResourceOperations``.
"""

from enum import StrEnum
from typing import (
    Any,
    Literal,
    override,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from ..utils.logging_config import get_resource_logger
from .consumer.mixin import ConsumerResourceSerializerMixin
from .exception_config import ExceptionConfig
from .finding_config import FindingConfig
from .notification_config import NotificationConfig

logger = get_resource_logger(__name__)

# Map API resource name (plural) to resource type for immutable-field lookup
RESOURCE_NAME_TO_TYPE: dict[str, str] = {
    "findings": "finding",
    "projects": "project",
    "policies": "policy",
    "namespaces": "namespace",
    "authorization-policies": "authorization_policy",
    "scan-profiles": "scan_profile",
    "repositories": "repository",
    "repository-versions": "repository_version",
    "package-versions": "package_version",
    "metrics": "metric",
    "linter-results": "linter_result",
    "dependency-metadata": "dependency_metadata",
    "installations": "installation",
    "package-licenses": "package_license",
    "semgrep-rules": "semgrep_rule",
    "scan-results": "scan_result",
    "notification-targets": "notification_target",
    "scan-workflows": "scan_workflow",
    "scan-workflow-results": "scan_workflow_result",
    "version-upgrades": "version_upgrade",
    "codeowners": "code_owners",
    "invitations": "invitation",
    "authentication-logs": "authentication_log",
    "endor-licenses": "endor_license",
    "policy-templates": "policy_template",
    "pr-comment-configs": "pr_comment_config",
}


class FlexibleEnum(StrEnum):
    """Base class for flexible enums that can handle unknown values."""

    @override
    @classmethod
    def _missing_(cls, value: str) -> "FlexibleEnum":  # pyright: ignore[reportIncompatibleMethodOverride]
        """Handle unknown enum values gracefully."""
        logger.info(
            "Unmodeled %s value from API: %s. Accepted as dynamic instance.",
            cls.__name__,
            value,
        )
        # Create a dynamic enum member for unknown values
        obj = str.__new__(cls, value)
        # Enum allows _name_/_value_ on dynamic members
        obj._name_ = value
        obj._value_ = value
        return obj


class JsonDefaultModel(BaseModel):
    """Pydantic base that defaults ``model_dump(mode='json')``.

    All model hierarchies that serialize for the Endor Labs API should
    inherit from this instead of ``BaseModel`` directly.  The single
    override here replaces five identical 30-line copies that used to
    live in TenantMeta, Context, BaseMeta, BaseSpec and BaseResource.
    """

    @override
    def model_dump(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        *,
        mode: Literal["json", "python"] = "json",
        include: set[str] | dict[str, Any] | None = None,
        exclude: set[str] | dict[str, Any] | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool = True,
        serialize_as_any: bool = False,
    ) -> dict[str, Any]:
        """Dump model with ``mode='json'`` by default.

        Ensures datetime objects and other non-JSON-serializable types
        are properly converted for API operations.
        """
        return super().model_dump(
            mode=mode,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )


class TenantMeta(JsonDefaultModel):
    """Base tenant metadata for all resources."""

    namespace: str = Field(..., description="Canonical namespace name")


class Context(JsonDefaultModel):
    """Contextual information for resources with context isolation."""

    id: str = Field(default="default", description="Context identifier")
    type: str = Field(..., description="Context type classification")


class ProcessingStatus(BaseModel):
    """Processing state for scannable resources."""

    disable_automated_scan: bool = Field(
        default=False, description="Disable automated scanning"
    )
    scan_state: str | None = Field(None, description="Current scan state")
    scan_time: str | None = Field(None, description="Last scan timestamp")
    analytic_time: str | None = Field(None, description="Last analytics timestamp")


class IngestedObject(BaseModel):
    """Ingestion metadata for external data."""

    ingestion_time: str = Field(..., description="Ingestion timestamp")
    raw: dict[str, Any] = Field(..., description="Raw object data")


class BaseMeta(JsonDefaultModel):
    """Base metadata for all resources with universal attributes."""

    model_config = ConfigDict(
        extra="allow", populate_by_name=True
    )  # Allow unknown fields for forward compatibility

    # Required universal fields (required per v1Meta; optional when list mask omits it)
    name: str | None = Field(
        None, description="Resource name"
    )  # IMMUTABLE: Set at creation
    kind: str | None = Field(
        None, description="Resource type identifier"
    )  # IMMUTABLE: Set at creation, but may be None when masked
    version: str | None = Field(
        None, description="Version identifier"
    )  # IMMUTABLE: System-managed, but may be None when masked

    # Lifecycle fields (auto-managed by API)
    create_time: str | None = Field(
        None, description="Creation timestamp"
    )  # IMMUTABLE: System-managed
    created_by: str | None = Field(
        None, description="Creator identifier"
    )  # IMMUTABLE: System-managed
    update_time: str | None = Field(
        None, description="Last update timestamp"
    )  # IMMUTABLE: System-managed
    updated_by: str | None = Field(
        None, description="Last updater identifier"
    )  # IMMUTABLE: System-managed
    upsert_time: str | None = Field(
        None, description="Upsert timestamp"
    )  # IMMUTABLE: System-managed

    # User-defined fields
    description: str | None = Field(
        None, description="Resource description"
    )  # MUTABLE: User can update
    tags: list[str] | None = Field(
        None, description="Resource tags"
    )  # MUTABLE: User can update
    annotations: dict[str, Any] | None = Field(
        None,
        description="Key-value metadata pairs",  # MUTABLE: User can update
    )

    @field_validator("annotations", mode="before")
    @classmethod
    def validate_annotations(cls, v: Any) -> Any:
        """Validate annotations field - allow any keys including 'id'."""
        # Annotations is a flexible dict that can contain any keys
        # The 'id' field is a known annotation key used by the API
        return v

    # Hierarchical fields
    parent_uuid: str | None = Field(
        None, description="Parent resource UUID"
    )  # IMMUTABLE: Set at creation
    parent_kind: str | None = Field(
        None, description="Parent resource kind"
    )  # IMMUTABLE: Set at creation

    # System fields
    references: dict[str, Any] | None = Field(
        None,
        description="External references and links",  # IMMUTABLE: System-managed
    )
    index_data: dict[str, Any] | None = Field(
        None,
        description="Search and indexing metadata",  # IMMUTABLE: System-managed
    )


class BaseSpec(JsonDefaultModel):
    """Base specification for all resources."""

    model_config = ConfigDict(
        extra="allow", populate_by_name=True
    )  # Allow unknown fields for forward compatibility

    # Schema drift fields - using typed models for better structure
    notification: NotificationConfig | None = Field(
        None, description="Notification configuration"
    )
    finding: FindingConfig | None = Field(None, description="Finding configuration")
    exception: ExceptionConfig | None = Field(
        None, description="Exception configuration"
    )


class BaseResource(JsonDefaultModel, ConsumerResourceSerializerMixin):
    """Base resource model for all Endor Labs resources.

    Field Mutability Guide:
    ======================

    IMMUTABLE FIELDS (cannot be updated after creation):
    - uuid: System-generated unique identifier
    - meta.name: Resource name set at creation
    - meta.kind: Resource type set at creation
    - meta.create_time: System-managed creation timestamp
    - meta.created_by: System-managed creator identifier
    - meta.update_time: System-managed update timestamp
    - meta.updated_by: System-managed updater identifier
    - meta.upsert_time: System-managed upsert timestamp
    - meta.parent_uuid: Parent relationship set at creation
    - meta.parent_kind: Parent type set at creation
    - meta.references: System-managed external references
    - meta.index_data: System-managed search metadata
    - tenant_meta.namespace: Tenant assignment (immutable)

    MUTABLE FIELDS (can be updated via API):
    - meta.description: User-defined description
    - meta.tags: User-defined tags list
    - meta.annotations: User-defined key-value metadata
    - spec.*: Most spec fields are mutable (resource-specific)

    The default implementation of get_mutable_fields_cls() returns only
    ["meta.description", "meta.tags"]. Subclasses override with
    resource-specific mutable paths (e.g. Project adds processing_status.*).
    """

    model_config = ConfigDict(
        extra="allow", populate_by_name=True
    )  # Allow unknown fields for forward compatibility

    # Universal fields (nearly universal)
    uuid: str = Field(
        ..., description="Unique identifier for the resource"
    )  # IMMUTABLE: System-generated
    meta: BaseMeta = Field(
        ..., description="Resource metadata"
    )  # Mixed: See BaseMeta field comments
    tenant_meta: TenantMeta | None = Field(
        None, description="Tenant metadata"
    )  # IMMUTABLE: Set at creation; None when list mask omits it

    # Common fields (88% present)
    spec: BaseSpec | None = Field(
        None, description="Resource specification"
    )  # MUTABLE: Most spec fields can be updated, but may be None when masked

    # Conditional fields (present when applicable)
    context: Context | None = Field(
        None, description="Contextual information"
    )  # MUTABLE: User can update
    processing_status: ProcessingStatus | None = Field(
        None,
        # PARTIALLY MUTABLE: scan_state and disable_automated_scan are updatable
        description="Processing state",
    )
    ingested_object: IngestedObject | None = Field(
        None,
        description="Ingestion metadata",  # IMMUTABLE: System-managed
    )
    related_object: dict[str, Any] | None = Field(
        None,
        description="Related object information",  # IMMUTABLE: System-managed
    )
    scan_object: dict[str, Any] | None = Field(
        None,
        description="Scan object information",  # IMMUTABLE: System-managed
    )
    propagate: bool | None = Field(
        None,
        description="Inheritance flag for hierarchical resources",  # MUTABLE
    )
