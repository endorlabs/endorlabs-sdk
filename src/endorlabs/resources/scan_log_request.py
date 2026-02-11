"""ScanLogRequest resource module for Endor Labs API.

This module provides operations for retrieving scan result logs via the
ScanLogRequest API. This is a request-based API (not standard CRUD).

API OPERATIONS SUPPORTED:
- POST: Create scan log request (retrieves logs in response)

API USAGE NOTES:
- ScanLogRequest is a request-based API, not a standard CRUD resource
- Create a request with filters to retrieve scan logs
- Logs are returned in the response's spec.log_messages array
- Can filter by scan_result_uuid, execution_id, project_uuid, etc.
- Namespace: the path namespace must be the one that owns the scan result
  (use the scan result's tenant_meta.namespace; parent namespace will fail).
- For more information, see the ScanLogRequestService REST API documentation
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
    FlexibleEnum,
)
from ..operations import BaseResourceOperations
from ..utils.logging_config import get_resource_logger

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


class ScanLogRequestLogMessage(BaseModel):
    """Log message structure returned in scan log requests."""

    level: ScanLogLevel | None = Field(None, description="Log level")
    json_payload: dict[str, Any] | None = Field(
        None, description="JSON payload of the message"
    )
    tags: dict[str, str] | None = Field(
        None, description="Tags associated with the log message"
    )
    timestamp: str | None = Field(
        None,
        description="Timestamp of the log message",
        json_schema_extra={"format": "date-time"},
    )


class ScanLogRequestMeta(BaseMeta):
    """Scan log request metadata extending BaseMeta."""

    # ScanLogRequest-specific fields only (universal fields inherited from BaseMeta)
    pass  # No additional fields needed, all were universal


class ScanLogRequestSpec(BaseSpec):
    """Scan log request specification extending BaseSpec.

    This spec is used both for creating requests (input) and receiving
    responses (output). The log_messages field is read-only and only
    present in responses.
    """

    # Required fields
    max_entries: int = Field(..., description="Maximum number of log entries to return")

    # Optional filter fields
    start_time: str | None = Field(
        None,
        description="Start time for log retrieval. If not defined, uses "
        "create time of corresponding scan request.",
        json_schema_extra={"format": "date-time"},
    )
    end_time: str | None = Field(
        None,
        description="End time cap for log retrieval. Default is 2 days "
        "from start_time.",
        json_schema_extra={"format": "date-time"},
    )
    newest_first: bool | None = Field(
        None, description="Return log entries in reverse chronological order"
    )
    log_levels: list[ScanLogLevel] | None = Field(
        None, description="Log levels to filter by"
    )

    # Filter by resource UUIDs
    scan_result_uuid: str | None = Field(
        None, description="UUID of scan result to filter logs"
    )
    execution_id: str | None = Field(
        None,
        description="Execution ID of scan to filter logs. Maps to "
        "spec.result.ci_run_uuid in ScanRequest and "
        "spec.environment.config.ExecutionID in ScanResult. "
        "Performance: Provide spec.start_time to avoid DB lookups.",
    )
    project_uuid: str | None = Field(None, description="Project UUID to filter logs")
    installation_uuid: str | None = Field(
        None, description="Installation UUID to filter logs"
    )
    scan_request_uuid: str | None = Field(
        None, description="Scan request UUID to filter logs"
    )
    onprem_scheduler_uuid: str | None = Field(
        None, description="On-prem scheduler UUID to filter logs"
    )

    # Admin-only fields
    admin_filter: str | None = Field(
        None, description="Extra filter available only for admin users"
    )

    # Read-only response fields
    applied_filter: str | None = Field(
        None,
        description="Filter that was applied to logs",
        json_schema_extra={"readOnly": True},
    )
    log_messages: list[ScanLogRequestLogMessage] | None = Field(
        None,
        description="Array of log messages (read-only, present in response)",
        json_schema_extra={"readOnly": True},
    )


class ScanLogRequest(BaseResource):
    """An Endor Labs ScanLogRequest entity extending BaseResource.

    ScanLogRequest-specific fields (universal fields inherited from BaseResource).

    OPERATION SUPPORT:
    ==================
    ✅ POST: Create scan log request (retrieves logs in response)
    ❌ GET: Not supported (request-based API)
    ❌ LIST: Not supported (request-based API)
    ❌ PATCH: Not supported (request-based API)
    ❌ DELETE: Not supported (request-based API)

    SPECIAL NOTES:
    ==============
    - This is a request-based API, not standard CRUD
    - Create a request with filters to retrieve scan logs
    - Logs are returned in spec.log_messages array
    - Use get_scan_result_logs() helper for convenience
    - UUID may be None in responses (request-based API)
    """

    # ScanLogRequest-specific fields (universal fields inherited from BaseResource)
    spec: ScanLogRequestSpec = Field(..., description="Scan log request specification")  # type: ignore
    uuid: str | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="UUID (may be None for request-based API)"
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data: Any) -> None:
        # Convert spec to ScanLogRequestSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = ScanLogRequestSpec(**data["spec"])
        super().__init__(**data)

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "max_entries",
                "start_time",
                "end_time",
                "newest_first",
                "log_levels",
                "scan_result_uuid",
                "execution_id",
                "project_uuid",
                "installation_uuid",
                "scan_request_uuid",
                "onprem_scheduler_uuid",
                "admin_filter",
                "applied_filter",
                "log_messages",
            }
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v


class ScanLogRequestSpecCreate(BaseModel):
    """Specification for creating a ScanLogRequest."""

    max_entries: int = Field(..., description="Maximum number of log entries to return")
    start_time: str | None = Field(
        None,
        description="Start time for log retrieval",
        json_schema_extra={"format": "date-time"},
    )
    end_time: str | None = Field(
        None,
        description="End time cap for log retrieval",
        json_schema_extra={"format": "date-time"},
    )
    newest_first: bool | None = Field(
        None, description="Return logs in reverse chronological order"
    )
    log_levels: list[ScanLogLevel] | None = Field(
        None, description="Log levels to filter by"
    )
    scan_result_uuid: str | None = Field(
        None, description="UUID of scan result to filter logs"
    )
    execution_id: str | None = Field(
        None, description="Execution ID of scan to filter logs"
    )
    project_uuid: str | None = Field(None, description="Project UUID to filter logs")
    installation_uuid: str | None = Field(
        None, description="Installation UUID to filter logs"
    )
    scan_request_uuid: str | None = Field(
        None, description="Scan request UUID to filter logs"
    )
    onprem_scheduler_uuid: str | None = Field(
        None, description="On-prem scheduler UUID to filter logs"
    )
    admin_filter: str | None = Field(None, description="Admin-only filter")


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
) -> list[ScanLogRequestLogMessage] | None:
    """Retrieve logs for a specific scan result.

    Convenience helper that creates a ScanLogRequest and extracts the log
    messages from the response.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Namespace that owns the scan result
            (e.g. scan_result.tenant_meta.namespace).
        scan_result_uuid: UUID of the scan result to get logs for
        max_entries: Maximum number of log entries to return (default: 100)
        log_levels: Optional list of log levels to filter by
        start_time: Optional start time for log retrieval (ISO format)
        end_time: Optional end time for log retrieval (ISO format)
        newest_first: Optional flag to return logs in reverse chronological order

    Returns:
        List of log messages if successful, None otherwise

    Example:
        >>> # Get error and warning logs for a scan result
        >>> logs = get_scan_result_logs(
        ...     client,
        ...     namespace,
        ...     "scan-result-uuid",
        ...     max_entries=50,
        ...     log_levels=[ScanLogLevel.ERROR, ScanLogLevel.WARNING]
        ... )
        >>> if logs:
        ...     for log in logs:
        ...         print(f"{log.timestamp} [{log.level}]: {log.json_payload}")

    """
    payload = CreateScanLogRequestPayload(
        meta=ScanLogRequestMetaCreate(name=f"scan-logs-{scan_result_uuid[:8]}"),
        spec=ScanLogRequestSpecCreate(
            max_entries=max_entries,
            scan_result_uuid=scan_result_uuid,
            log_levels=log_levels,
            start_time=start_time,
            end_time=end_time,
            newest_first=newest_first,
            execution_id=None,
            project_uuid=None,
            installation_uuid=None,
            scan_request_uuid=None,
            onprem_scheduler_uuid=None,
            admin_filter=None,
        ),
    )

    ops = BaseResourceOperations(client, "scan-log-requests", ScanLogRequest)
    request = ops.create(tenant_meta_namespace, payload)
    if request.spec and request.spec.log_messages:
        return request.spec.log_messages
    return []
