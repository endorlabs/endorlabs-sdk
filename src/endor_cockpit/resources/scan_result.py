"""
ScanResult resource module for Endor Labs API.

This module provides CRUD operations for ScanResult resources following the established
patterns from the Project and Finding resource implementations.

API OPERATIONS SUPPORTED:
- GET: List scan results, Get scan result by UUID
- POST: Create scan result (typically not used by end users)
- PATCH: Update scan result (limited mutability)
- DELETE: Delete scan result

API USAGE NOTES:
- ScanResults are typically generated automatically by endorctl or agentless scans
- Most fields are system-generated and read-only
- ScanResults contain scan configuration, environment details, runtime statistics,
  findings, policies triggered, and error logs
- For more information, see the ScanResultService REST API documentation
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient
from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseResourceOperations,
    BaseSpec,
    Context,
    FlexibleEnum,
)
from ..types import ListParameters

logger = logging.getLogger(__name__)


def _get_scan_result_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for scan results."""
    return BaseResourceOperations(client, "scan-results", ScanResult)


class ScanResultSpecStatus(FlexibleEnum):
    """Scan result status enumeration."""

    UNSPECIFIED = "STATUS_UNSPECIFIED"
    SUCCESS = "STATUS_SUCCESS"
    PARTIAL_SUCCESS = "STATUS_PARTIAL_SUCCESS"
    FAILURE = "STATUS_FAILURE"
    RUNNING = "STATUS_RUNNING"


class ScanResultSpecType(FlexibleEnum):
    """Scan result type enumeration."""

    UNSPECIFIED = "TYPE_UNSPECIFIED"
    GITHUB = "TYPE_GITHUB"
    GIT = "TYPE_GIT"
    ORG = "TYPE_ORG"
    PACKAGE = "TYPE_PACKAGE"
    ANALYTICS = "TYPE_ANALYTICS"
    FINDINGS = "TYPE_FINDINGS"
    SBOM_IMPORT = "TYPE_SBOM_IMPORT"
    TYPE_ALL_SCANS = "TYPE_ALL_SCANS"


class EndorctlRC(FlexibleEnum):
    """Endorctl exit code enumeration."""

    UNSPECIFIED = "ENDORCTL_RC_UNSPECIFIED"
    SUCCESS = "ENDORCTL_RC_SUCCESS"
    ERROR = "ENDORCTL_RC_ERROR"
    INVALID_ARGS = "ENDORCTL_RC_INVALID_ARGS"
    ENDOR_AUTH_FAILURE = "ENDORCTL_RC_ENDOR_AUTH_FAILURE"
    DOCTOR_FAILURE = "ENDORCTL_RC_DOCTOR_FAILURE"
    GITHUB_AUTH_FAILURE = "ENDORCTL_RC_GITHUB_AUTH_FAILURE"
    ANALYTICS_ERROR = "ENDORCTL_RC_ANALYTICS_ERROR"
    FINDINGS_ERROR = "ENDORCTL_RC_FINDINGS_ERROR"
    NOTIFICATIONS_ERROR = "ENDORCTL_RC_NOTIFICATIONS_ERROR"
    GITHUB_API_ERROR = "ENDORCTL_RC_GITHUB_API_ERROR"
    GITHUB_PERMISSIONS_ERROR = "ENDORCTL_RC_GITHUB_PERMISSIONS_ERROR"
    GIT_ERROR = "ENDORCTL_RC_GIT_ERROR"
    DEPENDENCY_RESOLUTION_ERROR = "ENDORCTL_RC_DEPENDENCY_RESOLUTION_ERROR"
    DEPENDENCY_SCANNING_ERROR = "ENDORCTL_RC_DEPENDENCY_SCANNING_ERROR"
    CALL_GRAPH_ERROR = "ENDORCTL_RC_CALL_GRAPH_ERROR"
    LINTER_ERROR = "ENDORCTL_RC_LINTER_ERROR"
    BAD_POLICY_TYPE = "ENDORCTL_RC_BAD_POLICY_TYPE"
    POLICY_ERROR = "ENDORCTL_RC_POLICY_ERROR"
    INTERNAL_ERROR = "ENDORCTL_RC_INTERNAL_ERROR"
    DEADLINE_EXCEEDED = "ENDORCTL_RC_DEADLINE_EXCEEDED"
    NOT_FOUND = "ENDORCTL_RC_NOT_FOUND"
    ALREADY_EXISTS = "ENDORCTL_RC_ALREADY_EXISTS"
    UNAUTHENTICATED = "ENDORCTL_RC_UNAUTHENTICATED"
    VULN_ERROR = "ENDORCTL_RC_VULN_ERROR"
    INITIALIZATION_ERROR = "ENDORCTL_RC_INITIALIZATION_ERROR"
    HOST_CHECK_FAILURE = "ENDORCTL_RC_HOST_CHECK_FAILURE"
    SBOM_IMPORT_ERROR = "ENDORCTL_RC_SBOM_IMPORT_ERROR"
    PRE_COMMIT_CHECK_FAILURE = "ENDORCTL_RC_PRE_COMMIT_CHECK_FAILURE"
    GH_ACTION_WORKFLOW_SCAN_FAILURE = "ENDORCTL_RC_GH_ACTION_WORKFLOW_SCAN_FAILURE"
    FILE_ANALYTICS_ERROR = "ENDORCTL_RC_FILE_ANALYTICS_ERROR"
    SIGNATURE_VERIFICATION_FAILURE = "ENDORCTL_RC_SIGNATURE_VERIFICATION_FAILURE"
    LICENSE_ERROR = "ENDORCTL_RC_LICENSE_ERROR"
    HUGGING_FACE_ERROR = "ENDORCTL_RC_HUGGING_FACE_ERROR"
    SAST_ERROR = "ENDORCTL_RC_SAST_ERROR"
    ARTIFACT_OPERATION_FAILURE = "ENDORCTL_RC_ARTIFACT_OPERATION_FAILURE"
    SEGMENTATION_ERROR = "ENDORCTL_RC_SEGMENTATION_ERROR"
    TOOLCHAIN_ERROR = "ENDORCTL_RC_TOOLCHAIN_ERROR"


class EnvironmentTool(BaseModel):
    """Environment tool information."""

    name: str = Field(..., description="Tool name")
    version: str = Field(..., description="Tool version")


class Environment(BaseModel):
    """Environment information for scan result.

    Contains host environment details and scan configuration.
    """

    arch: str = Field(..., description="CPU architecture")
    endorctl_version: str = Field(..., description="Endorctl version used")
    config: Dict[str, Any] = Field(
        ...,
        description="Configuration used by endorctl. Contains everything "
        "except credential values.",
    )
    os: str = Field(..., description="Operating system")
    memory: float = Field(..., description="Memory available (in bytes)")
    num_cpus: int = Field(..., description="Number of CPUs")
    tools: Optional[List[EnvironmentTool]] = Field(
        None, description="List of tools available in the environment"
    )


class SpecFindingData(BaseModel):
    """Finding data metadata (deprecated but kept for backward compatibility)."""

    uuid: Optional[str] = Field(None, description="Finding UUID")
    name: Optional[str] = Field(None, description="Finding name")
    description: Optional[str] = Field(None, description="Finding description")
    level: Optional[str] = Field(None, description="Finding level")
    tags: Optional[List[str]] = Field(None, description="Finding tags")
    categories: Optional[List[str]] = Field(None, description="Finding categories")
    approximation: Optional[bool] = Field(
        None, description="True if finding is for approximate dependency"
    )
    create_time: Optional[str] = Field(None, description="Finding creation time")


class ToolChainsSource(FlexibleEnum):
    """Toolchain source enumeration."""

    UNSPECIFIED = "TOOL_CHAINS_SOURCE_UNSPECIFIED"
    API = "TOOL_CHAINS_SOURCE_API"
    FILE = "TOOL_CHAINS_SOURCE_FILE"
    AUTO_DETECTION = "TOOL_CHAINS_SOURCE_AUTO_DETECTION"
    DEFAULTS = "TOOL_CHAINS_SOURCE_DEFAULTS"
    NAMESPACE_DEFAULT = "TOOL_CHAINS_SOURCE_NAMESPACE_DEFAULT"


class SpecProvisioningResultData(BaseModel):
    """Provisioning result data."""

    provisioning_result_uuid: str = Field(
        ..., description="UUID of the provisioning result"
    )
    exit_code: Optional[int] = Field(None, description="Provisioning exit code")
    error: Optional[str] = Field(None, description="Provisioning error message")
    automated_scan_parameters_config: Optional[Dict[str, Any]] = Field(
        None, description="Automated scan parameter configuration"
    )
    auto_detect_result: Optional[Dict[str, Any]] = Field(
        None, description="Auto detect results"
    )
    tool_chains_source: Optional[str] = Field(
        None, description="Toolchain source (enum: TOOL_CHAINS_SOURCE_*)"
    )
    tool_chains: Optional[Dict[str, Any]] = Field(
        None, description="Toolchains installed"
    )
    scan_profile: Optional[Dict[str, Any]] = Field(
        None, description="Scan profile used for provisioning"
    )


class Version(BaseModel):
    """Version information for a ref."""

    ref: str = Field(..., description="Resolved ref (tag, branch, or SHA)")
    sha: Optional[str] = Field(None, description="SHA of the source control version")
    metadata: Optional[Dict[str, str]] = Field(None, description="Version metadata")


class ScanResultMeta(BaseMeta):
    """Scan result metadata extending BaseMeta."""

    # ScanResult-specific fields only (universal fields inherited from BaseMeta)
    pass  # No additional fields needed, all were universal


class ScanResultSpec(BaseSpec):
    """Scan result specification extending BaseSpec.

    Field Mutability Guide:
    ======================

    FIELD MUTABILITY (per OpenAPI spec):
    =====================================
    Note: Most fields in v1ScanResultSpec are system-generated and should be
    treated as immutable in practice, even if not marked as readOnly in the spec.

    IMMUTABLE FIELDS (system-generated, read-only):
    - status: Scan status (set by scan execution)
    - type: Scan type (set to TYPE_ALL_SCANS by scan)
    - start_time, end_time: Scan timestamps (set by scan execution)
    - stats: Runtime statistics (calculated by scan)
    - refs: Branches scanned (determined by scan)
    - environment: Host environment details (captured at scan time)
    - has_panic: Panic indicator (set by scan execution)
    - exit_code: Exit code (set by scan execution)
    - logs: Scan output logs (generated by scan)
    - policies_triggered: Policies that matched (determined by scan)
    - warning_findings, blocking_findings, findings: Finding UUIDs (discovered by scan)
    - runtimes: Scan type runtimes (measured by scan)
    - languages_detected: Languages detected (discovered by scan)
    - deleted_findings: Findings deleted (determined by scan)
    - versions: Version information (determined by scan)
    - ecosystem_pkg_counts, ecosystem_dep_counts: Counts (calculated by scan)
    - provisioning_result: Provisioning data (set by scan)
    - errors, warnings, infos: Deprecated fields (legacy)
    - all_findings, exception_findings: Deprecated fields (legacy)

    MUTABLE FIELDS (if any):
    - None identified in practice (all fields are scan-generated)

    DEPRECATED FIELDS:
    - errors: Deprecated (use logs instead)
    - warnings: Deprecated (use logs instead)
    - infos: Deprecated (use logs instead)
    - all_findings: Deprecated
    - exception_findings: Deprecated
    """

    # Required fields
    status: ScanResultSpecStatus = Field(..., description="Success state of the scan")
    type: ScanResultSpecType = Field(
        ...,
        description="Type of scan that generated this scan result. "
        "Always set to TYPE_ALL_SCANS.",
    )

    # Optional fields
    start_time: Optional[str] = Field(
        None,
        description="Time the scan started",
        json_schema_extra={"format": "date-time"},
    )
    end_time: Optional[str] = Field(
        None,
        description="Time the scan ended",
        json_schema_extra={"format": "date-time"},
    )
    stats: Optional[Dict[str, int]] = Field(
        None,
        description="Map of stats such as how many issues were ingested "
        "during the scan.",
    )
    refs: Optional[List[str]] = Field(None, description="List of branches scanned")
    environment: Optional[Environment] = Field(
        None,
        description="All the information available about the input "
        "parameters and the host environment.",
    )
    has_panic: Optional[bool] = Field(
        None, description="True if there was a panic during the scan"
    )
    exit_code: Optional[EndorctlRC] = Field(
        None, description="The exit code of the scan"
    )
    logs: Optional[List[str]] = Field(
        None, description="User facing log output for the scan"
    )
    policies_triggered: Optional[List[str]] = Field(
        None, description="List of policy uuids triggered during the scan"
    )
    warning_findings: Optional[List[str]] = Field(
        None, description="List of warning finding uuids identified by the scan"
    )
    blocking_findings: Optional[List[str]] = Field(
        None, description="List of blocking finding uuids identified by the scan"
    )
    runtimes: Optional[Dict[str, int]] = Field(
        None,
        description="A map of internal scan type runtimes (in milliseconds) "
        "indexed by internal scan type string.",
    )
    findings: Optional[List[str]] = Field(
        None, description="List of all finding UUIDs identified by the scan"
    )
    deleted_findings: Optional[Dict[str, SpecFindingData]] = Field(
        None,
        description="Map of basic metadata for all findings deleted by the "
        "scan, indexed by finding uuid. Not available for CI runs.",
    )
    languages_detected: Optional[List[str]] = Field(
        None, description="List of languages detected by the scan"
    )
    provisioning_result_uuid: Optional[str] = Field(
        None, description="UUID of the provisioning result"
    )
    versions: Optional[List[Version]] = Field(
        None, description="Version information for each ref"
    )
    ecosystem_pkg_counts: Optional[Dict[str, int]] = Field(
        None,
        description="Number of package versions per ecosystems processed "
        "during the scan.",
    )
    ecosystem_dep_counts: Optional[Dict[str, int]] = Field(
        None,
        description="Number of dependencies per ecosystems processed during the scan.",
    )
    provisioning_result: Optional[SpecProvisioningResultData] = Field(
        None, description="Provisioning result data"
    )

    # Deprecated fields (kept for backward compatibility)
    errors: Optional[List[str]] = Field(
        None, description="Deprecated. Use logs instead."
    )
    warnings: Optional[List[str]] = Field(
        None, description="Deprecated. Use logs instead."
    )
    infos: Optional[List[str]] = Field(
        None, description="Deprecated. Use logs instead."
    )
    all_findings: Optional[Dict[str, SpecFindingData]] = Field(
        None, description="Deprecated."
    )
    exception_findings: Optional[Dict[str, SpecFindingData]] = Field(
        None, description="Deprecated."
    )


class ScanResult(BaseResource):
    """
    An Endor Labs ScanResult entity extending BaseResource.

    ScanResult-specific fields (universal fields inherited from BaseResource).

    OPERATION SUPPORT:
    ==================
    ✅ GET: List scan results, Get by UUID
    ✅ POST: Create scan result (typically not used by end users)
    ✅ PATCH: Update scan result (limited mutability)
    ✅ DELETE: Delete scan result

    FIELD MUTABILITY:
    =================
    IMMUTABLE FIELDS (readOnly: true in API spec):
    - uuid: Unique identifier (readOnly: true in v1ScanResult)
    - meta.create_time, meta.update_time, meta.upsert_time: Timestamps
      (readOnly: true in v1Meta)
    - meta.kind, meta.version: Resource metadata (readOnly: true in v1Meta)
    - meta.created_by, meta.updated_by: Audit fields (readOnly: true in v1Meta)
    - meta.references, meta.index_data: System-managed fields
      (readOnly: true in v1Meta)
    - tenant_meta.namespace: Namespace assignment
    - spec.*: Most spec fields are system-generated and immutable

    MUTABLE FIELDS (if any):
    - meta.tags: Resource tags (can be updated)
    - meta.description: Resource description (can be updated)
    - meta.annotations: Resource annotations (can be updated)

    Note: ScanResults are typically generated automatically by endorctl scans
    and most fields are read-only. Updates are generally limited to metadata.
    """

    # ScanResult-specific fields (universal fields inherited from BaseResource)
    spec: ScanResultSpec = Field(..., description="Scan result specification")  # type: ignore
    scan_result_context: Context = Field(
        ..., description="Context information for the scan result", alias="context"
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data):
        # Convert spec to ScanResultSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = ScanResultSpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "status",
                "type",
                "start_time",
                "end_time",
                "stats",
                "refs",
                "environment",
                "has_panic",
                "exit_code",
                "logs",
                "policies_triggered",
                "warning_findings",
                "blocking_findings",
                "runtimes",
                "findings",
                "deleted_findings",
                "languages_detected",
                "provisioning_result_uuid",
                "versions",
                "ecosystem_pkg_counts",
                "ecosystem_dep_counts",
                "provisioning_result",
                "errors",
                "warnings",
                "infos",
                "all_findings",
                "exception_findings",
            }
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v


class ScanResultMetaCreate(BaseModel):
    """Metadata for creating a ScanResult."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="The name of the scan result"
    )
    description: Optional[str] = Field(
        None, description="Description of the scan result"
    )


class ScanResultSpecCreate(BaseModel):
    """Specification for creating a ScanResult."""

    status: ScanResultSpecStatus = Field(..., description="Scan status")
    type: ScanResultSpecType = Field(..., description="Scan type")
    start_time: Optional[str] = Field(None, description="Scan start time")
    end_time: Optional[str] = Field(None, description="Scan end time")
    environment: Optional[Environment] = Field(None, description="Environment info")


class CreateScanResultPayload(BaseModel):
    """Payload for creating a new ScanResult."""

    meta: ScanResultMetaCreate
    spec: ScanResultSpecCreate
    context: Context


class ScanResultMetaUpdate(BaseModel):
    """Metadata for updating a ScanResult."""

    description: Optional[str] = Field(
        None, description="Updated description of the scan result"
    )
    tags: Optional[List[str]] = Field(
        None, description="Updated tags for the scan result"
    )
    annotations: Optional[Dict[str, Any]] = Field(
        None, description="Updated annotations for the scan result"
    )


class ScanResultSpecUpdate(BaseModel):
    """Specification for updating a ScanResult.

    Note: Most spec fields are system-generated and cannot be updated.
    This model exists for completeness but most fields are omitted.
    """

    pass  # No updatable spec fields identified


class UpdateScanResultPayload(BaseModel):
    """
    Payload for updating an Endor Labs ScanResult.

    MUTABLE FIELDS (can be updated via PATCH):
    - meta.tags: General resource tags
    - meta.description: Resource description
    - meta.annotations: Resource annotations

    IMMUTABLE FIELDS (read-only, managed by API):
    - uuid: Unique identifier (readOnly: true)
    - meta.name: Scan result name (set at creation)
    - meta.create_time, meta.update_time, meta.upsert_time: Timestamps
    - meta.kind, meta.version: Resource metadata
    - meta.created_by, meta.updated_by: Audit fields
    - meta.references, meta.index_data: System-managed fields
    - tenant_meta.namespace: Namespace assignment
    - spec.*: All spec fields are system-generated and immutable

    Example:
        >>> payload = UpdateScanResultPayload(
        ...     meta=ScanResultMetaUpdate(
        ...         tags=["reviewed", "test-scan"]
        ...     )
        ... )
        >>> scan_result = update_scan_result(
        ...     client, namespace, uuid, payload, "meta.tags"
        ... )
    """

    meta: Optional[ScanResultMetaUpdate] = Field(
        None, description="Updated scan result metadata"
    )
    spec: Optional[ScanResultSpecUpdate] = Field(
        None, description="Updated scan result specification"
    )
    context: Optional[Context] = Field(None, description="Updated scan result context")


def list_scan_results(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
) -> List[ScanResult]:
    """
    List scan results in a namespace.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name (e.g., 'tenant.namespace')
        list_params: Optional list parameters for filtering, pagination, etc.

    Returns:
        List of ScanResult objects
    """
    ops = _get_scan_result_ops(client)
    return ops.list(tenant_meta_namespace, list_params)  # type: ignore


def get_scan_result(
    client: APIClient, tenant_meta_namespace: str, scan_result_uuid: str
) -> Optional[ScanResult]:
    """
    Get a specific scan result by UUID.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        scan_result_uuid: UUID of the scan result to retrieve

    Returns:
        ScanResult object if found, None otherwise
    """
    ops = _get_scan_result_ops(client)
    return ops.get(tenant_meta_namespace, scan_result_uuid)  # type: ignore


def create_scan_result(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateScanResultPayload,
) -> Optional[ScanResult]:
    """
    Create a new scan result.

    Note: ScanResults are typically generated automatically by endorctl scans.
    This function is provided for completeness but is rarely used by end users.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        payload: ScanResult creation payload

    Returns:
        Created ScanResult object if successful, None otherwise
    """
    url = f"v1/namespaces/{tenant_meta_namespace}/scan-results"

    try:
        response = client.post(url, json=payload.model_dump())
        if response:
            data = response.json()
            return ScanResult(**data)
        return None
    except Exception as e:
        logger.error(f"Error creating scan result: {e}")
        return None


def update_scan_result(
    client: APIClient,
    tenant_meta_namespace: str,
    scan_result_uuid: str,
    payload: UpdateScanResultPayload,
    update_mask: Optional[str] = None,
) -> Optional[ScanResult]:
    """
    Update an existing scan result using partial updates.

    This function supports updating only specific fields using the update_mask
    parameter, which enables efficient partial updates without overwriting
    unchanged fields.

    MUTABLE FIELDS:
    - meta.tags: General resource tags
    - meta.description: Resource description
    - meta.annotations: Resource annotations

    FIELD MUTABILITY (per OpenAPI spec):
    =====================================
    IMMUTABLE FIELDS (readOnly: true in API spec):
    - uuid: Unique identifier (readOnly: true in UpdateScanResult request body)
    - meta.create_time, meta.update_time, meta.upsert_time: Timestamps
      (readOnly: true in v1Meta)
    - meta.kind, meta.version: Resource metadata (readOnly: true in v1Meta)
    - meta.created_by, meta.updated_by: Audit fields (readOnly: true in v1Meta)
    - meta.references, meta.index_data: System-managed fields
      (readOnly: true in v1Meta)
    - tenant_meta.namespace: Namespace assignment
    - spec.*: All spec fields are system-generated and immutable

    MUTABLE FIELDS (NOT readOnly in API spec):
    - meta.name, meta.description, meta.tags: Metadata
    - meta.annotations: Resource annotations

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        scan_result_uuid: UUID of the scan result to update
        payload: ScanResult update payload
        update_mask: Optional comma-separated list of fields to update
            (e.g., "meta.tags,meta.description"). If provided, only these
            fields will be updated. If omitted, all non-None fields in
            payload will be updated.

    Returns:
        Updated ScanResult object if successful, None otherwise

    Raises:
        requests.exceptions.HTTPError: For API-level errors (403, 404, etc.)
        pydantic.ValidationError: If response data doesn't match expected schema

    Example:
        >>> # Update scan result tags
        >>> payload = UpdateScanResultPayload(
        ...     meta=ScanResultMetaUpdate(tags=["reviewed", "test-scan"])
        ... )
        >>> scan_result = update_scan_result(
        ...     client, namespace, uuid, payload, "meta.tags"
        ... )
    """
    url = f"v1/namespaces/{tenant_meta_namespace}/scan-results"

    try:
        # Build update request body
        update_data = {
            "object": {
                "uuid": scan_result_uuid,
                **payload.model_dump(exclude_none=True),
            }
        }

        # Add update mask if provided
        if update_mask:
            update_data["request"] = {"update_mask": update_mask}

        response = client.patch(url, json=update_data)
        if response:
            data = response.json()
            return ScanResult(**data)
        return None
    except Exception as e:
        logger.error(f"Error updating scan result: {e}")
        return None


def delete_scan_result(
    client: APIClient, tenant_meta_namespace: str, scan_result_uuid: str
) -> bool:
    """
    Delete a scan result.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        scan_result_uuid: UUID of the scan result to delete

    Returns:
        True if deletion was successful, False otherwise
    """
    ops = _get_scan_result_ops(client)
    return ops.delete(tenant_meta_namespace, scan_result_uuid)
