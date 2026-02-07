"""Base model classes for Endor Labs resources.

This module provides base classes that define the common patterns
used across all Endor Labs resource models.
"""

import builtins
import logging
import os
import sys
from collections.abc import Iterator
from datetime import datetime
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    Self,
    TypeVar,
    Union,
    get_args,
    get_origin,
    override,
)

if TYPE_CHECKING:
    from ..api_client import APIClient

import contextlib

import httpx
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_serializer,
    field_validator,
)

from ..exceptions import (
    EndorAPIError,
)
from ..exceptions import (
    ValidationError as EndorValidationError,
)
from ..types import ListParameters, SupportsResourceUpdate
from ..utils.schema_drift import SchemaDriftDetector

# Import nested config models for better type safety
from .exception_config import ExceptionConfig
from .finding_config import FindingConfig
from .notification_config import NotificationConfig

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)

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
}


class FlexibleEnum(str, Enum):
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

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            # Skip drift detection for flexible dict fields
            flexible_dict_fields = {"annotations", "references", "index_data"}
            if info.field_name in flexible_dict_fields:
                return v  # These are flexible dicts that can contain any keys

            model_fields = {
                "name",
                "kind",
                "version",
                "create_time",
                "update_time",
                "created_by",
                "updated_by",
                "upsert_time",
                "description",
                "tags",
                "annotations",
                "parent_uuid",
                "parent_kind",
                "references",
                "index_data",
            }

            if info.field_name in model_fields:
                _ = SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields, f"BaseMeta.{info.field_name}"
                )
        return v


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

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift for unknown fields."""
        # Only check BaseSpec fields - subclasses handle their own drift detection
        # BaseSpec only has these optional fields:
        base_spec_fields = {
            "notification",  # NotificationConfig
            "finding",  # FindingConfig
            "exception",  # ExceptionConfig
            "git",  # GitInfo (in ProjectSpec)
        }

        # Only do drift detection if this is a BaseSpec field
        # Subclasses will handle their own fields in their validators
        if (
            info.field_name
            and isinstance(v, dict)
            and info.field_name in base_spec_fields
        ):
            # This is a BaseSpec field, check for unknown nested fields
            # But these are typed models, so let Pydantic handle validation
            # Skip drift detection here - typed models validate themselves
            pass
        return v


class BaseResource(JsonDefaultModel):
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

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift for unknown fields."""
        # Skip drift detection for typed nested models
        # (they handle their own validation)
        # Also skip "spec" - it's validated by subclass Spec models
        # (ScanProfileSpec, etc.)
        typed_model_fields = {
            "meta",  # BaseMeta - validated by BaseMeta
            "tenant_meta",  # TenantMeta - validated by TenantMeta
            "context",  # Context - validated by Context
            "processing_status",  # ProcessingStatus - validated by ProcessingStatus
            "ingested_object",  # IngestedObject - validated by IngestedObject
            "spec",  # BaseSpec or subclass - validated by Spec subclass validators
        }
        if (
            info.field_name
            and isinstance(v, dict)
            and info.field_name not in typed_model_fields
        ):
            model_fields = {
                "uuid",
                "meta",
                "spec",
                "tenant_meta",
                "context",
                "processing_status",
                "ingested_object",
                "related_object",
                "scan_object",
                "propagate",
            }

            if info.field_name in model_fields:
                # Extract resource name from class name (e.g., Finding -> Finding)
                resource_name = cls.__name__
                _ = SchemaDriftDetector.extract_unknown_fields(
                    v,
                    model_fields,
                    f"{resource_name}.{info.field_name}",
                    resource_name=resource_name,
                )
        return v

    @property
    def namespace(self) -> str | None:
        """Canonical namespace for this resource (tenant_meta.namespace or None)."""
        if self.tenant_meta is None:
            return None
        return getattr(self.tenant_meta, "namespace", None)

    @classmethod
    def get_mutable_fields_cls(cls) -> list[str]:
        """Get list of mutable fields for this resource type (class-level)."""
        return ["meta.description", "meta.tags"]

    def get_mutable_fields(self) -> list[str]:
        """Get list of mutable fields for this resource."""
        return type(self).get_mutable_fields_cls()

    def _path_to_kwarg(self, path: str) -> str:
        """Convert update_mask path to Python kwarg name."""
        if path.startswith("processing_status."):
            return path.split(".", 1)[1]
        return path.replace(".", "_")

    def get_update_kwarg_to_path(self) -> dict[str, str]:
        """Map kwarg names to update_mask paths for generic update."""
        return {self._path_to_kwarg(p): p for p in self.get_mutable_fields()}

    def _build_update_payload(self, **kwargs: Any) -> Self:
        """Build a copy of this resource with kwargs applied at their paths."""
        kwarg_to_path = self.get_update_kwarg_to_path()
        invalid = [k for k in kwargs if k not in kwarg_to_path]
        if invalid:
            raise TypeError(
                f"Invalid update kwargs for {type(self).__name__}: {invalid}. "
                f"Allowed: {list(kwarg_to_path)}"
            )
        result: Any = self
        for kwarg, value in kwargs.items():
            path = kwarg_to_path[kwarg]
            if "." not in path:
                result = result.model_copy(update={path: value})
                continue
            parent_path, field = path.rsplit(".", 1)
            parent = getattr(result, parent_path, None)
            if parent is None and parent_path == "processing_status":
                field_info = type(result).model_fields.get(parent_path)
                if field_info:
                    ann = getattr(field_info, "annotation", None)
                    if ann is not None and get_origin(ann) is Union:
                        ann = next(
                            (a for a in get_args(ann) if a is not type(None)),
                            ann,
                        )
                    if ann is not None:
                        try:
                            parent = ann(disable_automated_scan=False, scan_state="")
                        except Exception:
                            parent = None
            if parent is not None:
                dump = (
                    parent.model_dump()
                    if callable(getattr(parent, "model_dump", None))
                    else {}
                )
                merged = {**dump, field: value}
                new_parent = type(parent)(**merged)
                result = result.model_copy(update={parent_path: new_parent})
        return result

    def update(
        self,
        facade: SupportsResourceUpdate,
        **kwargs: Any,
    ) -> Self:
        """Update this resource with the given field kwargs; delegate to facade."""
        if not kwargs:
            raise TypeError(
                "Provide at least one field kwarg (e.g. meta_description=...) "
                "or use facade.update(resource, update_mask=..., payload=...)."
            )
        kwarg_to_path = self.get_update_kwarg_to_path()
        invalid = [k for k in kwargs if k not in kwarg_to_path]
        if invalid:
            raise TypeError(
                f"Invalid update kwargs for {type(self).__name__}: {invalid}. "
                f"Allowed: {list(kwarg_to_path)}"
            )
        payload = self._build_update_payload(**kwargs)
        update_mask = ",".join(kwarg_to_path[k] for k in kwargs)
        return facade.update(self, payload=payload, update_mask=update_mask)

    @classmethod
    def get_immutable_fields_cls(cls) -> list[str]:
        """Get list of immutable fields for this resource type (class-level).

        v1Meta readOnly (OpenAPI): create_time, update_time, upsert_time, kind,
        version, created_by, updated_by, references, index_data.
        """
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
        ]

    def get_immutable_fields(self) -> list[str]:
        """Get list of immutable fields for this resource."""
        return type(self).get_immutable_fields_cls()

    def validate_update_mask(self, update_mask: str) -> bool:
        """Validate that update_mask only contains mutable fields."""
        mutable_fields = self.get_mutable_fields()
        return update_mask in mutable_fields

    @field_serializer("*")
    def serialize_datetime(self, value: datetime | str) -> str:
        """Serialize datetime objects to ISO format strings."""
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @override
    def model_dump(
        self,
        *,
        mode: Literal["json", "python"] = "json",
        warnings: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Like ``JsonDefaultModel.model_dump`` but defaults ``warnings=False``.

        Suppresses Pydantic serializer warnings for nested
        meta/spec/tenant_meta/context models; pass ``warnings=True``
        to see them.
        """
        return super().model_dump(mode=mode, warnings=warnings, **kwargs)


class BaseResourceOperations(Generic[T]):
    """Base class providing CRUD operations for all resources."""

    def __init__(
        self,
        client: "APIClient",
        resource_name: str,
        model_class: type[T],
    ) -> None:
        super().__init__()
        self.client = client
        self.resource_name = resource_name
        self.model_class = model_class
        self.logger = logging.getLogger(f"{__name__}.{resource_name}")

    def _extract_items_from_page(self, data: Any) -> list[Any]:
        """Extract items from a paginated response page."""
        if "list" in data and "objects" in data["list"]:
            return data["list"]["objects"]
        elif isinstance(data, list):
            return data
        return []

    def _extract_page_token(self, data: Any) -> str | None:
        """Extract next page token from paginated response."""
        if isinstance(data, dict) and "list" in data:
            list_data = data["list"]
            if isinstance(list_data, dict) and "response" in list_data:
                response_data = list_data["response"]
                if isinstance(response_data, dict):
                    return response_data.get("next_page_token")
        return None

    def _safe_model_dump(
        self, model: BaseModel | None, exclude_none: bool = True
    ) -> dict[str, Any]:
        """Safely dump a Pydantic model to dictionary with JSON serialization.

        This method ensures datetime objects and other non-JSON-serializable
        types are properly serialized using mode="json".

        Args:
            model: Pydantic model instance to dump (can be None)
            exclude_none: Whether to exclude None values

        Returns:
            Dictionary representation of the model, or empty dict if model is None

        """
        if model is None:
            return {}
        return model.model_dump(exclude_none=exclude_none, mode="json", warnings=False)

    def _dump_for_api(
        self, model: BaseModel, exclude_none: bool = True
    ) -> dict[str, Any]:
        """Serialize model to dict for API request body.

        Single path for model-to-dict so all payloads use mode='json' and
        warnings=False, avoiding Pydantic serializer warnings for nested
        meta/spec/tenant_meta.
        """
        return model.model_dump(
            exclude_none=exclude_none, mode="json", warnings=False, by_alias=True
        )

    def dump_for_api(
        self, model: BaseModel, exclude_none: bool = True
    ) -> dict[str, Any]:
        """Public API to serialize a model to dict for request body (e.g. PATCH)."""
        return self._dump_for_api(model, exclude_none=exclude_none)

    def _to_request_body(
        self,
        resource: BaseModel,
        update_mask: builtins.list[str] | None,
        resource_uuid: str,
    ) -> dict[str, Any]:
        """Build the PATCH request 'object' dict from a resource model.

        Uses _dump_for_api then ensures uuid and applies sparse build when
        update_mask is present.
        """
        payload_dict = self._dump_for_api(resource)
        if "uuid" not in payload_dict:
            payload_dict["uuid"] = resource_uuid
        if update_mask:
            payload_dict = self._build_sparse_update_object(
                payload_dict, update_mask, resource_uuid
            )
        return payload_dict

    def _validate_payload(
        self, payload: BaseModel, operation: str, namespace: str
    ) -> BaseModel:
        """Pre-validate payload before API call.

        Validates the payload using Pydantic's model_validate to catch
        client-side validation errors before making API requests.

        Args:
            payload: Pydantic model instance to validate
            operation: Operation name (e.g., 'create', 'update')
            namespace: Namespace where operation will be performed

        Returns:
            Validated payload (same instance if valid)

        Raises:
            EndorValidationError: If payload validation fails

        """
        try:
            # Re-validate the payload to catch any issues
            # This ensures type safety and catches validation errors early
            validated = payload.model_validate(self._dump_for_api(payload))
            return validated
        except ValidationError as e:
            # Convert Pydantic ValidationError to our ValidationError
            raise EndorValidationError(
                message=f"Invalid payload for {operation} operation",
                operation=operation,
                namespace=namespace,
            ) from e

    @staticmethod
    def _build_sparse_update_object(
        payload_dict: dict[str, Any],
        update_mask: list[str],
        resource_uuid: str,
    ) -> dict[str, Any]:
        """Build a minimal request object containing only uuid and masked paths.

        Used when update_mask is present so the API receives only the fields
        being updated (sparse PATCH), not the full resource body.

        Args:
            payload_dict: Full payload as dict (nested).
            update_mask: List of field paths (e.g. ["meta.tags", "spec.finding_tags"]).
            resource_uuid: UUID to set in the result if not in payload.

        Returns:
            Dict with "uuid" and only the nested values for paths in update_mask.
            Paths missing in payload_dict are skipped (no KeyError).

        """
        result: dict[str, Any] = {
            "uuid": payload_dict.get("uuid", resource_uuid),
        }
        for path in update_mask:
            parts = path.strip().split(".")
            try:
                value: Any = payload_dict
                for key in parts:
                    value = value[key]
            except (KeyError, TypeError):
                continue
            target = result
            for key in parts[:-1]:
                if key not in target:
                    target[key] = {}
                target = target[key]
            target[parts[-1]] = value
        return result

    def _process_grpc_error(
        self, grpc_code: int, error_message: str | None
    ) -> tuple[int, str, str] | None:
        """Process gRPC error codes."""
        (
            grpc_http_code,
            error_context,
            user_message,
        ) = self.client._get_grpc_error_context(grpc_code)  # pyright: ignore[reportPrivateUsage]

        # If gRPC code is documented, use its context
        if grpc_http_code is not None:
            # For Code 3 (INVALID_ARGUMENT), always use parsed message
            # (contains specific validation details like "Invalid filter path")
            # For other codes, prefer parsed message, fallback to user message
            if error_message:
                final_message = error_message
            elif user_message:
                final_message = user_message
            else:
                final_message = "An error occurred"

            return (grpc_http_code, final_message, error_context)
        return None

    def _extract_from_http_error(
        self, e: httpx.HTTPStatusError
    ) -> tuple[int | None, str, str]:
        """Extract details from HTTPStatusError."""
        status_code = e.response.status_code
        # Parse error response to get gRPC code and message
        grpc_code, error_message = self.client._parse_error_response_succinct(  # pyright: ignore[reportPrivateUsage]
            e.response
        )

        # Try to get error context from gRPC code first (more specific)
        if grpc_code is not None:
            result = self._process_grpc_error(grpc_code, error_message)
            if result:
                return result

        # Fallback to HTTP status code mapping for undocumented gRPC codes
        if status_code == 400:
            return (status_code, error_message, "Validation error")
        elif status_code == 403:
            return (status_code, error_message, "Permission denied")
        elif status_code == 404:
            return (status_code, error_message, "Resource not found")
        elif status_code == 401:
            return (status_code, error_message, "Authentication failed")
        elif status_code == 429:
            return (status_code, error_message, "Rate limit exceeded")
        elif status_code >= 500:
            return (status_code, error_message, "Server error")
        else:
            return (status_code, error_message, f"HTTP error {status_code}")

    def _extract_error_details(self, e: Exception) -> tuple[int | None, str, str]:
        """Extract error details from exception.

        Uses gRPC codes when available for more accurate error classification,
        falls back to HTTP status codes for undocumented errors.

        Args:
            e: The exception to extract details from

        Returns:
            Tuple of (status_code, error_message, error_context)
            - status_code: HTTP status code if available, None otherwise
            - error_message: User-friendly error message
            - error_context: Human-readable error context description

        """
        if isinstance(e, httpx.HTTPStatusError) and hasattr(e, "response"):
            return self._extract_from_http_error(e)

        # Unobserved error (non-HTTP exception)
        return (None, str(e), "Unexpected error")

    def _log_error_with_response(
        self, e: Exception, operation: str, tenant_meta_namespace: str, **kwargs: Any
    ) -> None:
        """Log error with full response text for HTTPStatusError exceptions.

        Args:
            e: The exception to log
            operation: Operation name (e.g., "create", "update", "delete")
            tenant_meta_namespace: Namespace where operation was attempted
            **kwargs: Additional context (e.g., resource_uuid for update/delete)

        """
        status_code, error_msg, error_context = self._extract_error_details(e)
        from pydantic import ValidationError

        is_validation_error = isinstance(e, ValidationError)

        # Extract full response text for HTTPStatusError exceptions
        response_text = ""
        if isinstance(e, httpx.HTTPStatusError) and hasattr(e, "response"):
            with contextlib.suppress(Exception):
                response_text = e.response.text

        # Build error message with response text if available
        if response_text:
            full_error_msg = f"{error_msg}. Response: {response_text}"
        else:
            full_error_msg = error_msg

        # Build resource identifier for error message
        resource_id = ""
        if "resource_uuid" in kwargs:
            resource_id = f" UUID '{kwargs['resource_uuid']}'"

        # Log error with appropriate message based on status code
        if status_code == 400:
            self.logger.error(
                f"Failed to {operation} {self.resource_name}{resource_id} in namespace "
                f"'{tenant_meta_namespace}': {full_error_msg}"
            )
        elif status_code == 403:
            self.logger.error(
                f"Failed to {operation} {self.resource_name}{resource_id} in namespace "
                f"'{tenant_meta_namespace}': Permission denied. {full_error_msg}"
            )
        elif status_code == 404:
            self.logger.error(
                f"Failed to {operation} {self.resource_name}{resource_id} in namespace "
                f"'{tenant_meta_namespace}': Resource not found."
            )
        elif status_code == 409:
            self.logger.error(
                f"Failed to {operation} {self.resource_name}{resource_id} in namespace "
                f"'{tenant_meta_namespace}': Conflict. {full_error_msg}"
            )
        elif status_code is not None:
            self.logger.error(
                f"Failed to {operation} {self.resource_name}{resource_id} in namespace "
                f"'{tenant_meta_namespace}': {error_context}. {full_error_msg}"
            )
        else:
            self.logger.error(
                f"Failed to {operation} {self.resource_name}{resource_id} in namespace "
                f"'{tenant_meta_namespace}': {full_error_msg}. "
                f"Check payload validity and API connectivity.",
                exc_info=is_validation_error,
            )

    def list(
        self,
        tenant_meta_namespace: str,
        list_params: ListParameters | None = None,
        max_pages: int | None = None,
        **kwargs: Any,
    ) -> list[T]:
        """Universal list operation with automatic pagination.

        Args:
            tenant_meta_namespace: Namespace to list resources from
            list_params: Optional list parameters (filter, page_size, etc.)
            max_pages: Optional maximum number of pages to fetch.
                If None and in test environment, defaults to 10 pages max.
                If None in production, fetches all pages.
            **kwargs: Additional keyword arguments (e.g. filter, page_size).

        Returns:
            List of resource objects

        """
        kwargs.pop("logging_level", None)  # Session-level only; ignore if passed
        try:
            url = f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}"

            # Check if we're in a test environment and set default max_pages
            import os

            if max_pages is None and (
                "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST")
            ):
                # Default to 10 pages max in test environment for safety
                max_pages = 10
                self.logger.debug(
                    f"Test environment detected: limiting pagination to "
                    f"{max_pages} pages max"
                )

            traverse = getattr(list_params, "traverse", None) if list_params else None
            self.logger.info(
                "Listing %s in namespace %s (traverse=%s, max_pages=%s).",
                self.resource_name,
                tenant_meta_namespace,
                traverse,
                max_pages,
            )

            # Build query parameters once
            params = self._build_params(list_params, **kwargs)

            # Use get_all() for pagination instead of manual loop
            all_items = list(
                self.client.get_all(
                    url,
                    params=params,
                    max_pages=max_pages,
                )
            )

            self.logger.info(
                "Listed %s %s.",
                len(all_items),
                self.resource_name,
            )
            self.logger.debug(
                f"Fetched {len(all_items)} {self.resource_name} items "
                f"from namespace '{tenant_meta_namespace}'"
            )

            return [self.model_class(**item) for item in all_items]

        except EndorAPIError as e:
            # Re-raise our custom exceptions
            raise e from None
        except httpx.HTTPStatusError as e:
            # Map HTTP errors to typed exceptions
            raise self.client.map_http_error_to_exception(
                e, "list", tenant_meta_namespace
            ) from e
        except ValidationError as e:
            # Pydantic validation error on response
            from ..exceptions import ServerError

            error_details = "\n".join(
                f"  {err['loc']}: {err['msg']} (type: {err['type']})"
                for err in e.errors()
            )
            raise ServerError(
                message=(
                    f"Response validation failed for {self.resource_name} "
                    f"in namespace '{tenant_meta_namespace}'. "
                    f"Validation details:\n{error_details}"
                ),
                operation="list",
                namespace=tenant_meta_namespace,
                response_text=str(e.errors()),
            ) from e
        except Exception as e:
            # Unexpected errors
            from ..exceptions import ServerError

            raise ServerError(
                message=(
                    f"Unexpected error listing {self.resource_name} "
                    f"in namespace '{tenant_meta_namespace}': {e!s}"
                ),
                operation="list",
                namespace=tenant_meta_namespace,
            ) from e

    def list_iter(
        self,
        tenant_meta_namespace: str,
        list_params: ListParameters | None = None,
        max_pages: int | None = None,
        **kwargs: Any,
    ) -> Iterator[T]:
        """Yield resources from a paginated list without materializing the full list.

        Same URL and params as list(); yields one model per item from get_all().
        """
        kwargs.pop("logging_level", None)  # Session-level only; ignore if passed
        url = f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}"
        if max_pages is None and (
            "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST")
        ):
            max_pages = 10
            self.logger.debug(f"Test env: limiting pagination to {max_pages} pages max")
        params = self._build_params(list_params, **kwargs)
        for item in self.client.get_all(url, params=params, max_pages=max_pages):
            yield self.model_class(**item)

    def get(self, tenant_meta_namespace: str, resource_uuid: str) -> T:
        """Universal get operation with fallback to list+filter.

        Raises:
            NotFoundError: If resource doesn't exist
            PermissionDeniedError: If user lacks permission
            ServerError: If server error occurs

        """
        try:
            # Method 1: Try direct UUID access first (fastest if it works)
            res = self.client.get(
                f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}/"
                f"{resource_uuid}"
            )
            data = res.json()
            return self.model_class(**data)
        except EndorAPIError as e:
            # Re-raise our custom exceptions
            raise e from None
        except httpx.HTTPStatusError as e:
            # For 404, try fallback method; for other errors, raise immediately
            if e.response.status_code == 404:
                # 404 is expected when falling back, use debug level
                self.logger.debug(
                    f"Direct {self.resource_name} access failed for UUID "
                    f"'{resource_uuid}' in namespace '{tenant_meta_namespace}'. "
                    f"Falling back to list+filter approach."
                )
            else:
                # Other HTTP errors - raise immediately
                raise self.client.map_http_error_to_exception(
                    e, "get", tenant_meta_namespace, resource_uuid=resource_uuid
                ) from e
        except Exception as e:
            # For non-HTTP errors, try fallback
            self.logger.debug(
                f"Direct {self.resource_name} access failed for UUID "
                f"'{resource_uuid}' in namespace '{tenant_meta_namespace}': "
                f"{e!s}. Falling back to list+filter approach."
            )

        # Method 2: Use list and filter approach (workaround)
        try:
            list_params = ListParameters(  # pyright: ignore[reportCallIssue]
                filter=f"uuid=={resource_uuid}",
                traverse=True,  # Enable traversal to search child namespaces
            )
            resources = self.list(tenant_meta_namespace, list_params)
            if resources:
                return resources[0]
            # No resources found - raise NotFoundError
            from ..exceptions import NotFoundError

            raise NotFoundError(
                message=(
                    f"{self.resource_name} with UUID '{resource_uuid}' "
                    f"not found in namespace '{tenant_meta_namespace}'"
                ),
                operation="get",
                namespace=tenant_meta_namespace,
                resource_uuid=resource_uuid,
            )
        except EndorAPIError as e:
            # Re-raise our custom exceptions
            raise e from None
        except httpx.HTTPStatusError as e:
            # Map HTTP errors to typed exceptions
            raise self.client.map_http_error_to_exception(
                e, "get", tenant_meta_namespace, resource_uuid=resource_uuid
            ) from e
        except Exception as e:
            # Unexpected errors
            from ..exceptions import ServerError

            raise ServerError(
                message=(
                    f"Unexpected error getting {self.resource_name} "
                    f"UUID '{resource_uuid}': {e!s}"
                ),
                operation="get",
                namespace=tenant_meta_namespace,
                resource_uuid=resource_uuid,
            ) from e

    def create(self, tenant_meta_namespace: str, payload: BaseModel) -> T:
        """Universal create operation with pre-validation and typed errors.

        Optional: set ENDOR_CREATE_TIMEOUT (seconds) in the environment to use
        a request timeout for create calls (e.g. 60 for slow endpoints like
        scan-log-requests).

        Raises:
            EndorValidationError: If payload validation fails
            NotFoundError: If namespace doesn't exist
            PermissionDeniedError: If user lacks permission
            ConflictError: If resource already exists
            ServerError: If server error occurs

        """
        # Pre-validate payload before API call
        validated_payload = self._validate_payload(
            payload, "create", tenant_meta_namespace
        )

        try:
            url = f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}"

            # Convert payload to dict
            payload_dict = self._dump_for_api(validated_payload)

            # DEBUG: Log request payload
            self.logger.debug(
                f"Creating {self.resource_name} in namespace "
                f"'{tenant_meta_namespace}' with payload: {payload_dict}"
            )

            # Optional create timeout (e.g. for slow endpoints like scan-log-requests)
            create_timeout: int | float | None = None
            env_timeout = os.environ.get("ENDOR_CREATE_TIMEOUT")
            if env_timeout is not None:
                try:
                    create_timeout = int(env_timeout)
                except ValueError:
                    create_timeout = None
            post_kwargs: dict[str, Any] = {}
            if create_timeout is not None:
                post_kwargs["timeout"] = create_timeout

            res = self.client.post(url, json=payload_dict, **post_kwargs)
            data = res.json()

            # Validate response structure
            if not isinstance(data, dict):
                from ..exceptions import ServerError

                raise ServerError(
                    message=(
                        f"Invalid response format for {self.resource_name}: "
                        f"expected dict, got {type(data)}"
                    ),
                    operation="create",
                    namespace=tenant_meta_namespace,
                    response_text=str(data),
                )

            if "uuid" not in data:
                self.logger.warning(
                    f"Response missing UUID for {self.resource_name}: {data}"
                )

            # DEBUG: Log successful response
            self.logger.debug(
                f"Successfully created {self.resource_name}: "
                f"{data.get('uuid', 'unknown')}"
            )

            return self.model_class(**data)
        except EndorAPIError as e:
            # Re-raise our custom exceptions
            raise e from None
        except httpx.HTTPStatusError as e:
            # Map HTTP errors to typed exceptions
            raise self.client.map_http_error_to_exception(
                e, "create", tenant_meta_namespace
            ) from e
        except ValidationError as e:
            # Pydantic validation error on response
            from ..exceptions import ServerError

            raise ServerError(
                message=(
                    f"Response validation failed for {self.resource_name} "
                    f"in namespace '{tenant_meta_namespace}'"
                ),
                operation="create",
                namespace=tenant_meta_namespace,
                response_text=str(e.errors()),
            ) from e
        except Exception as e:
            # Unexpected errors
            from ..exceptions import ServerError

            raise ServerError(
                message=f"Unexpected error creating {self.resource_name}: {e!s}",
                operation="create",
                namespace=tenant_meta_namespace,
            ) from e

    def update(
        self,
        tenant_meta_namespace: str,
        resource_uuid: str,
        payload: BaseModel,
        update_mask: builtins.list[str],
    ) -> T:
        """Universal update operation with field masking and pre-validation.

        update_mask is required and must contain at least one field path; sparse
        PATCH is always used so the full object is never sent.

        Raises:
            EndorValidationError: If payload validation fails or update_mask is
                empty or contains immutable fields
            NotFoundError: If resource doesn't exist
            PermissionDeniedError: If user lacks permission
            ServerError: If server error occurs

        """
        if not update_mask:
            raise EndorValidationError(
                message=(
                    f"{self.resource_name} update requires a non-empty update_mask "
                    "(e.g. ['meta.description', 'meta.tags'])."
                ),
                operation="update",
                namespace=tenant_meta_namespace,
                resource_uuid=resource_uuid,
            )

        # Pre-validate payload before API call
        validated_payload = self._validate_payload(
            payload, "update", tenant_meta_namespace
        )

        # Block immutable fields in update_mask (model is canonical)
        get_immutable = getattr(self.model_class, "get_immutable_fields_cls", None)
        immutable: list[str] = get_immutable() if get_immutable is not None else []
        for path in update_mask:
            if path.strip() in immutable:
                raise EndorValidationError(
                    message=f"Cannot update immutable field: {path.strip()}",
                    operation="update",
                    namespace=tenant_meta_namespace,
                    resource_uuid=resource_uuid,
                )

        try:
            # Use collection endpoint (UUID goes in request body, not URL path)
            url = f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}"

            # Convert payload to dict (single path: _to_request_body)
            payload_dict = self._to_request_body(
                validated_payload, update_mask, resource_uuid
            )

            # Warn if payload has unmodeled (extra) attributes
            extra = getattr(validated_payload, "__pydantic_extra__", None)
            if extra:
                self.logger.warning(
                    "Unmodeled attributes in update payload: %s",
                    list(extra.keys()),
                )

            # Build request body with object and required update_mask
            request_data = {
                "object": payload_dict,
                "request": {"update_mask": ",".join(update_mask)},
            }

            # DEBUG: Log update request
            self.logger.debug(
                f"Updating {self.resource_name} UUID '{resource_uuid}' in namespace "
                f"'{tenant_meta_namespace}' with update_mask: {update_mask}"
            )

            res = self.client.patch(url, json=request_data)
            data = res.json()

            # DEBUG: Log successful update
            self.logger.debug(
                f"Successfully updated {self.resource_name} UUID '{resource_uuid}'"
            )

            return self.model_class(**data)

        except EndorAPIError as e:
            # Re-raise our custom exceptions
            raise e from None
        except httpx.HTTPStatusError as e:
            # Map HTTP errors to typed exceptions
            raise self.client.map_http_error_to_exception(
                e, "update", tenant_meta_namespace, resource_uuid=resource_uuid
            ) from e
        except ValidationError as e:
            # Pydantic validation error on response
            from ..exceptions import ServerError

            raise ServerError(
                message=(
                    f"Response validation failed for {self.resource_name} UUID "
                    f"'{resource_uuid}' in namespace '{tenant_meta_namespace}'"
                ),
                operation="update",
                namespace=tenant_meta_namespace,
                resource_uuid=resource_uuid,
                response_text=str(e.errors()),
            ) from e
        except Exception as e:
            # Unexpected errors
            from ..exceptions import ServerError

            raise ServerError(
                message=(
                    f"Unexpected error updating {self.resource_name} "
                    f"UUID '{resource_uuid}': {e!s}"
                ),
                operation="update",
                namespace=tenant_meta_namespace,
                resource_uuid=resource_uuid,
            ) from e

    def delete(self, tenant_meta_namespace: str, resource_uuid: str) -> bool:
        """Universal delete operation.

        Returns:
            True if deletion was successful (status 200 or 204)

        Raises:
            NotFoundError: If resource doesn't exist
            PermissionDeniedError: If user lacks permission
            ServerError: If server error occurs

        """
        try:
            url = (
                f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}/"
                f"{resource_uuid}"
            )

            res = self.client.delete(url)

            # Check if deletion was successful (204 No Content or 200 OK)
            if res.status_code in [200, 204]:
                return True
            # Unexpected status code - raise error
            from ..exceptions import ServerError

            raise ServerError(
                message=(
                    f"Unexpected status code {res.status_code} "
                    f"when deleting {self.resource_name} UUID '{resource_uuid}'"
                ),
                status_code=res.status_code,
                operation="delete",
                namespace=tenant_meta_namespace,
                resource_uuid=resource_uuid,
            )

        except EndorAPIError as e:
            # Re-raise our custom exceptions
            raise e from None
        except httpx.HTTPStatusError as e:
            # Map HTTP errors to typed exceptions
            raise self.client.map_http_error_to_exception(
                e, "delete", tenant_meta_namespace, resource_uuid=resource_uuid
            ) from e
        except Exception as e:
            # Unexpected errors
            from ..exceptions import ServerError

            raise ServerError(
                message=(
                    f"Unexpected error deleting {self.resource_name} "
                    f"UUID '{resource_uuid}': {e!s}"
                ),
                operation="delete",
                namespace=tenant_meta_namespace,
                resource_uuid=resource_uuid,
            ) from e

    def count(
        self, tenant_meta_namespace: str, list_params: ListParameters | None = None
    ) -> int:
        """Count resources matching filter criteria."""
        try:
            # Create count-specific list parameters
            if list_params:
                count_params = list_params
                count_params.count = True
            else:
                count_params = ListParameters(count=True)  # pyright: ignore[reportCallIssue]

            url = f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}"

            # Build query parameters
            params = self._build_params(count_params)

            res = self.client.get(url, params=params)
            data = res.json()

            # Handle count response
            if "list" in data and "response" in data["list"]:
                return data["list"]["response"].get("total", 0)
            elif "total" in data:
                return data["total"]
            else:
                return 0

        except Exception as e:
            status_code, error_msg, error_context = self._extract_error_details(e)

            # Log error with appropriate message based on status code
            if status_code == 400:
                self.logger.error(
                    f"Failed to count {self.resource_name} in namespace "
                    f"'{tenant_meta_namespace}': {error_msg}"
                )
            elif status_code == 403:
                self.logger.error(
                    f"Failed to count {self.resource_name} in namespace "
                    f"'{tenant_meta_namespace}': Permission denied. {error_msg}"
                )
            elif status_code is not None:
                self.logger.error(
                    f"Failed to count {self.resource_name} in namespace "
                    f"'{tenant_meta_namespace}': {error_context}. {error_msg}"
                )
            else:
                self.logger.error(
                    f"Failed to count {self.resource_name} in namespace "
                    f"'{tenant_meta_namespace}': {error_msg}. "
                    f"Check namespace permissions and filter syntax.",
                    exc_info=True,
                )
            return 0

    def _build_params(
        self, list_params: ListParameters | None, **kwargs: Any
    ) -> dict[str, Any]:
        """Build query parameters from list_params and kwargs."""
        params = {}

        if list_params:
            self._add_basic_params(params, list_params)
            self._add_pagination_params(params, list_params)
            self._add_sorting_params(params, list_params)
            self._add_boolean_params(params, list_params)
            self._add_date_params(params, list_params)
            self._add_extra_list_params(params, list_params)
            self._add_group_params(params, list_params)

        # Add any additional kwargs
        params.update(kwargs)

        return params

    def _add_basic_params(
        self, params: dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add basic filter and mask parameters."""
        if list_params.filter:
            params["list_parameters.filter"] = list_params.filter
        if list_params.mask:
            params["list_parameters.mask"] = list_params.mask

    def _add_pagination_params(
        self, params: dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add pagination-related parameters.

        Note: page_size is only added if explicitly set. If None, the API
        will use its default page size (typically 100). This is intentional
        to avoid performance issues with small page sizes.
        """
        # Only add page_size if explicitly set (don't override API default)
        if list_params.page_size is not None:
            params["list_parameters.page_size"] = str(list_params.page_size)
        if list_params.page_token:
            params["list_parameters.page_token"] = list_params.page_token
        if list_params.page_id:
            params["list_parameters.page_id"] = list_params.page_id

    def _add_sorting_params(
        self, params: dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add sorting-related parameters.

        API expects list_parameters.sort.path and list_parameters.sort.order
        (enum: SORT_ENTRY_ORDER_ASC, SORT_ENTRY_ORDER_DESC).
        Prefer sort_by + desc; fall back to sort_field + sort_order with normalization.
        """
        path: str | None = None
        order: str | None = None
        if list_params.sort_by:
            path = list_params.sort_by
            order = (
                "SORT_ENTRY_ORDER_DESC" if list_params.desc else "SORT_ENTRY_ORDER_ASC"
            )
        elif list_params.sort_field:
            path = list_params.sort_field
            raw = (list_params.sort_order or "asc").lower()
            order = (
                "SORT_ENTRY_ORDER_DESC"
                if raw in ("desc", "descending")
                else "SORT_ENTRY_ORDER_ASC"
            )
        if path:
            params["list_parameters.sort.path"] = path
        if order:
            params["list_parameters.sort.order"] = order

    def _add_boolean_params(
        self, params: dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add boolean parameters."""
        if list_params.count is not None:
            params["list_parameters.count"] = str(list_params.count).lower()

        # Handle traverse parameter (canonical way to traverse namespaces)
        if list_params.traverse is not None:
            # API uses 'list_parameters.traverse' as the query parameter
            params["list_parameters.traverse"] = str(list_params.traverse).lower()
        if list_params.archive is not None:
            params["list_parameters.archive"] = str(list_params.archive).lower()
        if list_params.list_all is not None:
            params["list_parameters.list_all"] = str(list_params.list_all).lower()

    def _add_extra_list_params(
        self, params: dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add extra common list parameters (pr_uuid, etc.)."""
        if list_params.pr_uuid:
            params["list_parameters.pr_uuid"] = list_params.pr_uuid

    def _add_group_params(
        self, params: dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add grouping/aggregation list parameters."""
        if list_params.group_aggregation_paths:
            params["list_parameters.group_aggregation_paths"] = ",".join(
                list_params.group_aggregation_paths
            )
        if list_params.group_by_time is not None:
            params["list_parameters.group_by_time"] = str(
                list_params.group_by_time
            ).lower()
        if list_params.group_by_time_field_value:
            params["list_parameters.group_by_time_field_value"] = (
                list_params.group_by_time_field_value
            )
        if list_params.group_by_time_interval:
            params["list_parameters.group_by_time_interval"] = (
                list_params.group_by_time_interval
            )
        if list_params.group_by_time_mode:
            params["list_parameters.group_by_time_mode"] = (
                list_params.group_by_time_mode
            )
        if list_params.group_by_time_operator:
            params["list_parameters.group_by_time_operator"] = (
                list_params.group_by_time_operator
            )
        if list_params.group_show_aggregation_uuids is not None:
            params["list_parameters.group_show_aggregation_uuids"] = str(
                list_params.group_show_aggregation_uuids
            ).lower()
        if list_params.group_unique_count_paths:
            params["list_parameters.group_unique_count_paths"] = ",".join(
                list_params.group_unique_count_paths
            )
        if list_params.group_unique_value_paths:
            params["list_parameters.group_unique_value_paths"] = ",".join(
                list_params.group_unique_value_paths
            )

    def _add_date_params(
        self, params: dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add date-related parameters."""
        if list_params.from_date:
            params["list_parameters.from_date"] = list_params.from_date
        if list_params.to_date:
            params["list_parameters.to_date"] = list_params.to_date
