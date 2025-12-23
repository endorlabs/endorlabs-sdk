"""
AuditLog resource module for Endor Labs API.

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

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from ..api_client import APIClient
from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseResourceOperations,
    BaseSpec,
    FlexibleEnum,
)
from ..types import ListParameters

logger = logging.getLogger(__name__)

# Global resource instance
_audit_log_ops = None


def _get_audit_log_ops(client: APIClient) -> BaseResourceOperations:
    """Get or create audit log operations instance."""
    global _audit_log_ops
    if _audit_log_ops is None:
        _audit_log_ops = BaseResourceOperations(client, "audit-logs", AuditLog)
    return _audit_log_ops


class AuditLogOperation(FlexibleEnum):
    """Audit log operation type enumeration."""

    UNSPECIFIED = "OPERATION_UNSPECIFIED"
    CREATE = "OPERATION_CREATE"
    UPDATE = "OPERATION_UPDATE"
    DELETE = "OPERATION_DELETE"
    UPSERT = "OPERATION_UPSERT"


class AuditLogSpec(BaseSpec):
    """Audit log specification extending BaseSpec."""

    message_uuid: Optional[str] = Field(
        None,
        description=(
            "The UUID of the resource which was accessed/modified in this operation"
        ),
    )
    message_kind: Optional[str] = Field(
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
    payload: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "The operation payload containing the message that was "
            "created or updated (protobuf Any format)"
        ),
    )
    error: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Error information if the operation failed "
            "(gRPC Status format with code, message, details)"
        ),
    )
    claims: Optional[List[str]] = Field(
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
    remote_address: Optional[str] = Field(
        None, description="The source IP address of the request"
    )

    @field_validator("claims")
    @classmethod
    def validate_claims(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate claims are not empty strings."""
        if v:
            return [claim.strip() for claim in v if claim.strip()]
        return v


class AuditLogMeta(BaseMeta):
    """Audit log metadata extending BaseMeta."""

    # No additional fields needed - BaseMeta provides all required fields
    pass


class AuditLog(BaseResource):
    """
    Audit Log resource model extending BaseResource.

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
    spec: Optional[AuditLogSpec] = Field(None, description="Audit log specification")  # type: ignore

    model_config = {"extra": "ignore"}

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
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
    propagate: Optional[bool] = Field(
        False, description="Propagate to child namespaces"
    )


def list_audit_logs(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
    **kwargs,
) -> List[AuditLog]:
    """
    List active audit logs in the specified namespace (last 30 days).

    Active audit logs remain in the active database for 30 days before being
    automatically moved to archive storage. Use list_archived_audit_logs()
    for logs older than 30 days.

    Args:
        client: Authenticated APIClient instance
        tenant_meta_namespace: Target tenant namespace (canonical name)
        list_params: Optional list parameters for filtering/pagination
        **kwargs: Additional query parameters

    Returns:
        List of AuditLog resources

    Example:
        >>> from endor_cockpit.api_client import APIClient
        >>> from endor_cockpit.types import ListParameters
        >>> client = APIClient()
        >>> # List all audit logs
        >>> logs = list_audit_logs(client, "tenant.namespace")
        >>> # Filter by operation type
        >>> creates = list_audit_logs(
        ...     client, "tenant.namespace",
        ...     list_params=ListParameters(
        ...         filter="spec.operation=='OPERATION_CREATE'"
        ...     )
        ... )
        >>> # Filter by time range
        >>> recent = list_audit_logs(
        ...     client, "tenant.namespace",
        ...     list_params=ListParameters(
        ...         filter=(
        ...             "meta.create_time>=date(2025-01-01T00:00:00Z) "
        ...             "and meta.create_time<=date(2025-01-31T23:59:59Z)"
        ...         )
        ...     )
        ... )
    """
    ops = _get_audit_log_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)  # type: ignore


def list_archived_audit_logs(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
    **kwargs,
) -> List[AuditLog]:
    """
    List archived audit logs in the specified namespace (30+ days old).

    Archived audit logs are logs older than 30 days that have been moved to
    archive storage. They are retained for 3 years. Both active and archived
    logs support the same filters, pagination, and field masks.

    Note: When retrieving archived audit logs, filter by spec.message_kind
    first, followed by meta.create_time for optimal query performance. The
    meta.create_time filter must be used in conjunction with spec.message_kind.

    Args:
        client: Authenticated APIClient instance
        tenant_meta_namespace: Target tenant namespace (canonical name)
        list_params: Optional list parameters for filtering/pagination
        **kwargs: Additional query parameters

    Returns:
        List of AuditLog resources

    Example:
        >>> from endor_cockpit.api_client import APIClient
        >>> from endor_cockpit.types import ListParameters
        >>> client = APIClient()
        >>> # List all archived audit logs
        >>> archived = list_archived_audit_logs(client, "tenant.namespace")
        >>> # Filter archived logs by message kind and time
        >>> old_policies = list_archived_audit_logs(
        ...     client, "tenant.namespace",
        ...     list_params=ListParameters(
        ...         filter=(
        ...             "spec.message_kind=="
        ...             "'internal.endor.ai.endor.v1.Policy' "
        ...             "and meta.create_time>=date(2024-01-01T00:00:00Z)"
        ...         )
        ...     )
        ... )
    """
    try:
        url = f"v1/namespaces/{tenant_meta_namespace}/audit-logs/archived"
        ops = _get_audit_log_ops(client)

        # Use BaseResourceOperations to build params and handle pagination
        # but override the URL to use archived endpoint
        all_items = []
        page_token = None
        page_count = 0
        max_pages = kwargs.pop("max_pages", None)

        while True:
            # Check max_pages limit
            if max_pages is not None and page_count >= max_pages:
                logger.warning(
                    f"Reached max_pages limit ({max_pages}). "
                    f"Stopping pagination after {page_count} pages. "
                    f"Fetched {len(all_items)} items so far."
                )
                break

            # Build query parameters using BaseResourceOperations helper
            params = ops._build_params(list_params, **kwargs)

            # Add page_token to params if present
            if page_token is not None:
                params["list_parameters.page_token"] = str(page_token)

            res = client.get(url, params=params)
            data = res.json()

            # Extract objects from this page
            items = ops._extract_items_from_page(data)
            all_items.extend(items)
            page_count += 1

            # Check for next page token
            page_token = ops._extract_page_token(data)

            # Break if no more pages
            if not page_token:
                break

        logger.debug(
            f"Fetched {len(all_items)} archived audit log items "
            f"across {page_count} pages from namespace "
            f"'{tenant_meta_namespace}'"
        )

        return [AuditLog(**item) for item in all_items]

    except Exception as e:
        logger.error(
            f"Failed to list archived audit logs in namespace "
            f"'{tenant_meta_namespace}': {e}"
        )
        return []


def get_audit_log(
    client: APIClient, tenant_meta_namespace: str, audit_log_uuid: str
) -> Optional[AuditLog]:
    """
    Get an audit log by UUID.

    Args:
        client: Authenticated APIClient instance
        tenant_meta_namespace: Target tenant namespace (canonical name)
        audit_log_uuid: UUID of the audit log

    Returns:
        AuditLog resource or None if not found

    Example:
        >>> from endor_cockpit.api_client import APIClient
        >>> client = APIClient()
        >>> log = get_audit_log(client, "tenant.namespace", "uuid-here")
        >>> if log:
        ...     print(f"Operation: {log.spec.operation}")
        ...     print(f"Message Kind: {log.spec.message_kind}")
    """
    ops = _get_audit_log_ops(client)
    return ops.get(tenant_meta_namespace, audit_log_uuid)  # type: ignore


def create_audit_log(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateAuditLogPayload,
) -> Optional[AuditLog]:
    """
    Create a new audit log entry (manual creation).

    Note: Audit logs are typically system-generated. Manual creation is
    available for special use cases.

    Args:
        client: Authenticated APIClient instance
        tenant_meta_namespace: Target tenant namespace (canonical name)
        payload: Audit log creation payload

    Returns:
        Created AuditLog resource or None if creation failed

    Example:
        >>> from endor_cockpit.api_client import APIClient
        >>> from endor_cockpit.resources.audit_log import (
        ...     CreateAuditLogPayload, AuditLogMeta, AuditLogSpec,
        ...     AuditLogOperation
        ... )
        >>> client = APIClient()
        >>> payload = CreateAuditLogPayload(
        ...     meta=AuditLogMeta(
        ...         name="manual-audit-log",
        ...         description="Manually created audit log"
        ...     ),
        ...     spec=AuditLogSpec(
        ...         operation=AuditLogOperation.CREATE,
        ...         message_kind="internal.endor.ai.endor.v1.Policy"
        ...     )
        ... )
        >>> log = create_audit_log(client, "tenant.namespace", payload)
    """
    try:
        ops = _get_audit_log_ops(client)
        return ops.create(tenant_meta_namespace, payload)  # type: ignore
    except Exception as e:
        logger.error(
            f"Failed to create audit log in namespace '{tenant_meta_namespace}': {e}"
        )
        return None


def delete_audit_log(
    client: APIClient, tenant_meta_namespace: str, audit_log_uuid: str
) -> bool:
    """
    Delete an audit log by UUID.

    Args:
        client: Authenticated APIClient instance
        tenant_meta_namespace: Target tenant namespace (canonical name)
        audit_log_uuid: UUID of the audit log to delete

    Returns:
        True if deletion succeeded, False otherwise

    Example:
        >>> from endor_cockpit.api_client import APIClient
        >>> client = APIClient()
        >>> success = delete_audit_log(
        ...     client, "tenant.namespace", "uuid-here"
        ... )
        >>> if success:
        ...     print("Audit log deleted successfully")
    """
    ops = _get_audit_log_ops(client)
    return ops.delete(tenant_meta_namespace, audit_log_uuid)
