"""AuditLog — thin consumer wrapper over generated V1AuditLog."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator

from endorlabs.generated.models.audit_log_service import V1AuditLog

from .base import BaseMeta, BaseSpec, FlexibleEnum
from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class AuditLog(V1AuditLog, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for AuditLog (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("AuditLog")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("AuditLog")


# --- integration / create-update compat (pre-cutover helpers) ---


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


class CreateAuditLogPayload(BaseModel):
    """Payload for creating a new audit log entry."""

    meta: AuditLogMeta = Field(..., description="Audit log metadata")
    spec: AuditLogSpec = Field(..., description="Audit log specification")
    propagate: bool | None = Field(False, description="Propagate to child namespaces")


def build_create_payload(**kwargs: Any) -> CreateAuditLogPayload:
    """Build CreateAuditLogPayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateAuditLogPayload, kwargs, attr_name="AuditLog"
    )
