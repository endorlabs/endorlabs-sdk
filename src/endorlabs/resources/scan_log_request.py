"""ScanLogRequest — thin consumer wrapper over generated V1ScanLogRequest."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, Field, model_validator

from endorlabs.generated.models.scan_log_request_service import (
    V1LogLevel,
    V1ScanLogRequest,
    V1ScanLogRequestLogMessage,
)

from ..utils.logging_config import get_resource_logger
from .base import FlexibleEnum
from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin, ScanLogRequestSpec

if TYPE_CHECKING:
    from ..api_client import APIClient

logger = get_resource_logger(__name__)


class ScanLogLevel(FlexibleEnum):
    """Scan log level enumeration."""

    UNSPECIFIED = "LOG_LEVEL_UNSPECIFIED"
    EMERGENCY = "LOG_LEVEL_EMERGENCY"
    ALERT = "LOG_LEVEL_ALERT"
    CRITICAL = "LOG_LEVEL_CRITICAL"
    ERROR = "LOG_LEVEL_ERROR"
    WARNING = "LOG_LEVEL_WARNING"
    NOTICE = "LOG_LEVEL_NOTICE"
    INFO = "LOG_LEVEL_INFO"
    DEBUG = "LOG_LEVEL_DEBUG"


ScanLogRequestLogMessage = V1ScanLogRequestLogMessage


class ScanLogRequest(
    V1ScanLogRequest, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for ScanLogRequest (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("ScanLogRequest")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("ScanLogRequest")

    spec: ScanLogRequestSpec | None = None  # pyright: ignore[reportIncompatibleVariableOverride]

    @model_validator(mode="before")
    @classmethod
    def _coerce_spec_dict(cls, data: Any) -> Any:
        from .consumer.wire_compat import coerce_legacy_tenant_meta

        data = coerce_legacy_tenant_meta(data)
        if isinstance(data, dict) and isinstance(data.get("spec"), dict):
            data = {**data, "spec": ScanLogRequestSpec(**data["spec"])}
        return data


class ScanLogRequestSpecCreate(BaseModel):
    """Specification for creating a ScanLogRequest."""

    max_entries: int = Field(..., description="Maximum number of log entries to return")
    start_time: str | None = None
    end_time: str | None = None
    newest_first: bool | None = None
    log_levels: list[ScanLogLevel | V1LogLevel | str] | None = None
    scan_result_uuid: str | None = None
    execution_id: str | None = None
    project_uuid: str | None = None
    installation_uuid: str | None = None
    scan_request_uuid: str | None = None
    onprem_scheduler_uuid: str | None = None
    admin_filter: str | None = None


class ScanLogRequestMetaCreate(BaseModel):
    """Metadata for creating a ScanLogRequest."""

    name: str = Field(..., description="Name for the log request (required)")


class CreateScanLogRequestPayload(BaseModel):
    """Payload for creating a new ScanLogRequest."""

    meta: ScanLogRequestMetaCreate = Field(
        ..., description="Metadata (required by API)"
    )
    spec: ScanLogRequestSpecCreate


def get_scan_result_logs(
    client: APIClient,
    tenant_meta_namespace: str,
    scan_result_uuid: str,
    max_entries: int = 100,
    log_levels: list[ScanLogLevel] | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    newest_first: bool | None = None,
) -> list[V1ScanLogRequestLogMessage] | None:
    """Retrieve logs for a specific scan result."""
    from endorlabs.operations import BaseResourceOperations

    payload = CreateScanLogRequestPayload(
        meta=ScanLogRequestMetaCreate(name=f"scan-logs-{scan_result_uuid[:8]}"),
        spec=ScanLogRequestSpecCreate(
            max_entries=max_entries,
            scan_result_uuid=scan_result_uuid,
            log_levels=log_levels,
            start_time=start_time,
            end_time=end_time,
            newest_first=newest_first,
        ),
    )

    ops = BaseResourceOperations(client, "scan-log-requests", ScanLogRequest)
    request = ops.create(tenant_meta_namespace, payload)
    if request.spec and request.spec.log_messages:
        return request.spec.log_messages
    return []
