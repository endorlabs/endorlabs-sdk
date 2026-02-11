"""AuditLog resource module for Endor Labs API.

This module provides comprehensive audit log querying capabilities including
listing, examining, and filtering audit logs to track user actions and system
operations for compliance and security monitoring.

API OPERATIONS SUPPORTED:
- GET: List audit logs, Get audit log by UUID, List archived audit logs
- POST: Create audit log entry (manual)
- DELETE: Delete audit log entry

API FEATURES:
- Active audit logs (last 30 days)
- Archived audit logs (30+ days old, retained for 3 years)
- Filtering by operation type, message kind, time range, claims, IP address
- Support for identifying API key activity via claims filtering
- Pagination support for large result sets
- Field masking for performance optimization

AUDIT LOG RETENTION:
- Active logs: 30 days in active database
- Archived logs: 3 years in archive storage
- Both support same filters, pagination, and field masks

TIMEOUT CONSIDERATIONS:
Audit log queries may take longer than other API operations. Default timeout
is 20 seconds. Use --timeout option to override if needed.
"""

from __future__ import annotations

from typing import Any, ClassVar, override

from pydantic import BaseModel, Field, field_validator

from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
    FlexibleEnum,
)
from ..utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)


class AuditLogOperation(FlexibleEnum):
    """Audit log operation type enumeration."""

    UNSPECIFIED = "OPERATION_UNSPECIFIED"
    CREATE = "OPERATION_CREATE"
    UPDATE = "OPERATION_UPDATE"
    DELETE = "OPERATION_DELETE"
    UPSERT = "OPERATION_UPSERT"


class AuditLogError(BaseModel):
    """Error information when an audit log operation failed (gRPC Status-like)."""

    code: int | None = Field(None, description="Error code.")
    message: str | None = Field(None, description="Error message.")
    details: list[Any] | None = Field(
        None,
        description="Additional error details (list of objects or strings).",
    )


class AuditLogSpec(BaseSpec):
    """Audit log specification extending BaseSpec."""

    message_uuid: str | None = Field(
        None,
        description=(
            "The UUID of the resource which was accessed/modified in this operation"
        ),
    )
    message_kind: str | None = Field(
        None,
        description=(
            "The kind of the message/resource type. "
            "Example: 'internal.endor.ai.endor.v1.Policy'"
        ),
    )
    operation: AuditLogOperation = Field(
        ...,
        description=(
            "The type of operation performed (CREATE, UPDATE, DELETE, UPSERT)"
        ),
    )
    payload: dict[str, Any] | None = Field(
        None,
        description=(
            "The operation payload containing the message that was "
            "created or updated (protobuf Any format)"
        ),
    )
    error: AuditLogError | None = Field(
        None,
        description=(
            "Error information if the operation failed "
            "(gRPC Status format with code, message, details)"
        ),
    )
    claims: list[str] | None = Field(
        None,
        description=(
            "Authentication claims array containing authentication "
            "information. Used to identify API key activity.\n\n"
            "Example claims:\n"
            "  - 'ID=19946263398469405566117368291178288812'\n"
            "  - 'email=scheduler@endor.ai'\n"
            "  - 'user=scheduler@endor.ai@x509'\n"
            "  - 'api-key' (indicates API key authentication)\n"
            "  - 'issuer=https://api.endorlabs.com/v1'"
        ),
    )
    remote_address: str | None = Field(
        None, description="The source IP address of the request"
    )

    @field_validator("claims")
    @classmethod
    def validate_claims(cls, v: list[str] | None) -> list[str] | None:
        """Validate claims are not empty strings."""
        if v:
            return [claim.strip() for claim in v if claim.strip()]
        return v


class AuditLogMeta(BaseMeta):
    """Audit log metadata extending BaseMeta."""

    # No additional fields needed - BaseMeta provides all required fields
    pass


class AuditLog(BaseResource):
    """Audit Log resource model extending BaseResource.

    OPERATION SUPPORT:
    ==================
    ✅ GET: List audit logs, Get by UUID, List archived audit logs
    ✅ POST: Create audit log entry (manual)
    ✅ DELETE: Delete audit log entry
    ❌ PATCH: Audit logs are immutable (cannot be updated)

    FIELD MUTABILITY:
    =================
    IMMUTABLE FIELDS (read-only, system-managed):
    - uuid: Unique identifier
    - meta.create_time, meta.created_by: Creation metadata
    - meta.update_time, meta.updated_by: Auto-managed timestamps
    - spec.operation: Operation type (set at creation)
    - spec.message_uuid: Resource UUID (set at creation)
    - spec.message_kind: Resource type (set at creation)
    - spec.payload: Operation payload (set at creation)
    - spec.claims: Authentication claims (set at creation)
    - spec.remote_address: Source IP (set at creation)
    - tenant_meta.namespace: Namespace assignment

    FEATURES:
    =========
    - Active logs: Last 30 days in active database
    - Archived logs: 30+ days old, retained for 3 years
    - Filtering by operation, message kind, time range, claims, IP
    - API key identification via spec.claims filtering
    - Pagination support for large result sets
    - Field masking for performance optimization
    - Timeout considerations (default 20s, can override)

    USAGE EXAMPLES:
    ===============
    # List all audit logs
    logs = list_audit_logs(client, "tenant.namespace")

    # Filter by operation type
    creates = list_audit_logs(
        client, "tenant.namespace",
        list_params=ListParameters(
            filter="spec.operation=='OPERATION_CREATE'"
        )
    )

    # Filter by time range
    recent = list_audit_logs(
        client, "tenant.namespace",
        list_params=ListParameters(
            filter=(
                "meta.create_time>=date(2025-01-01T00:00:00Z) "
                "and meta.create_time<=date(2025-01-31T23:59:59Z)"
            )
        )
    )

    # Identify API key activity via claims
    api_key_activity = list_audit_logs(
        client, "tenant.namespace",
        list_params=ListParameters(
            filter="spec.claims matches '.*api-key.*'"
        )
    )

    # List archived logs (30+ days old)
    archived = list_archived_audit_logs(client, "tenant.namespace")
    """

    # Audit log-specific fields (universal fields inherited from BaseResource)
    spec: AuditLogSpec | None = Field(None, description="Audit log specification")  # type: ignore

    model_config: ClassVar[dict[str, str]] = {"extra": "ignore"}

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift in audit log responses."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "message_uuid",
                "message_kind",
                "operation",
                "payload",
                "error",
                "claims",
                "remote_address",
            }

            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )

        return v


class CreateAuditLogPayload(BaseModel):
    """Payload for creating a new audit log entry."""

    meta: AuditLogMeta = Field(..., description="Audit log metadata")
    spec: AuditLogSpec = Field(..., description="Audit log specification")
    propagate: bool | None = Field(False, description="Propagate to child namespaces")


def build_create_payload(**kwargs: Any) -> CreateAuditLogPayload:
    """Build CreateAuditLogPayload from kwargs (decoupled facade create)."""
    return CreateAuditLogPayload(**kwargs)
