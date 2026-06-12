"""ScanResult resource module for Endor Labs API.

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

from __future__ import annotations

from typing import Any, override

from pydantic import BaseModel, ConfigDict, Field

from ..utils.logging_config import get_resource_logger
from .base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
    Context,
    FlexibleEnum,
)

logger = get_resource_logger(__name__)


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
    ADMISSION_POLICIES = "TYPE_ADMISSION_POLICIES"
    ALERT_POLICIES = "TYPE_ALERT_POLICIES"
    ALL_SCANS = "TYPE_ALL_SCANS"
    ANALYTICS = "TYPE_ANALYTICS"
    ANALYTICS_CHECK = "TYPE_ANALYTICS_CHECK"
    CALL_GRAPH = "TYPE_CALL_GRAPH"
    DEPENDENCY_RESOLUTION = "TYPE_DEPENDENCY_RESOLUTION"
    DOCTOR = "TYPE_DOCTOR"
    EXCEPTION_POLICIES = "TYPE_EXCEPTION_POLICIES"
    FILE_ANALYTICS = "TYPE_FILE_ANALYTICS"
    FINDINGS = "TYPE_FINDINGS"
    GIT = "TYPE_GIT"
    GITHUB = "TYPE_GITHUB"
    HOST_CHECK = "TYPE_HOST_CHECK"
    HUGGING_FACE = "TYPE_HUGGING_FACE"
    LICENSE_DISCOVERY = "TYPE_LICENSE_DISCOVERY"
    LINTER = "TYPE_LINTER"
    NOTIFICATION_POLICIES = "TYPE_NOTIFICATION_POLICIES"
    ORG = "TYPE_ORG"
    PACKAGE = "TYPE_PACKAGE"
    PR_SECURITY_REVIEW = "TYPE_PR_SECURITY_REVIEW"
    PROVISIONING = "TYPE_PROVISIONING"
    SBOM_IMPORT = "TYPE_SBOM_IMPORT"
    UIA = "TYPE_UIA"
    WORKFLOW_SCAN = "TYPE_WORKFLOW_SCAN"


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
    SANDBOX_ERROR = "ENDORCTL_RC_SANDBOX_ERROR"
    RULE_SET_ERROR = "ENDORCTL_RC_RULE_SET_ERROR"
    SECURITY_REVIEW_ERROR = "ENDORCTL_RC_SECURITY_REVIEW_ERROR"
    CODE_API_ERROR = "ENDORCTL_RC_CODE_API_ERROR"
    POLICY_VIOLATION = "ENDORCTL_RC_POLICY_VIOLATION"
    POLICY_WARNING = "ENDORCTL_RC_POLICY_WARNING"
    PR_SECURITY_REVIEW_ERROR = "ENDORCTL_RC_PR_SECURITY_REVIEW_ERROR"
    EXPORTER_WARNING = "ENDORCTL_RC_EXPORTER_WARNING"
    CONTAINER_PROFILING_WARNING = "ENDORCTL_RC_CONTAINER_PROFILING_WARNING"


class EnvironmentTool(BaseModel):
    """Environment tool information."""

    name: str = Field(..., description="Tool name")
    version: str = Field(..., description="Tool version")


class Environment(BaseModel):
    """Environment information for scan result.

    Contains host environment details and scan configuration.
    """

    model_config = ConfigDict(
        extra="allow"
    )  # Allow unknown fields for forward compatibility

    arch: str = Field(..., description="CPU architecture")
    endorctl_version: str = Field(..., description="Endorctl version used")
    config: dict[str, Any] = Field(
        ...,
        description="Configuration used by endorctl. Contains everything "
        "except credential values.",
    )
    os: str = Field(..., description="Operating system")
    memory: float = Field(..., description="Memory available (in bytes)")
    num_cpus: int = Field(..., description="Number of CPUs")
    tools: list[EnvironmentTool] | None = Field(
        None, description="List of tools available in the environment"
    )


class SpecFindingData(BaseModel):
    """Finding data metadata (deprecated but kept for backward compatibility)."""

    uuid: str | None = Field(None, description="Finding UUID")
    name: str | None = Field(None, description="Finding name")
    description: str | None = Field(None, description="Finding description")
    level: str | None = Field(None, description="Finding level")
    tags: list[str] | None = Field(None, description="Finding tags")
    categories: list[str] | None = Field(None, description="Finding categories")
    approximation: bool | None = Field(
        None, description="True if finding is for approximate dependency"
    )
    create_time: str | None = Field(None, description="Finding creation time")


class ToolChainsSource(FlexibleEnum):
    """Toolchain source enumeration."""

    UNSPECIFIED = "TOOL_CHAINS_SOURCE_UNSPECIFIED"
    API = "TOOL_CHAINS_SOURCE_API"
    AUTO_DETECTION = "TOOL_CHAINS_SOURCE_AUTO_DETECTION"
    DEFAULTS = "TOOL_CHAINS_SOURCE_DEFAULTS"
    FILE = "TOOL_CHAINS_SOURCE_FILE"
    NAMESPACE_DEFAULT = "TOOL_CHAINS_SOURCE_NAMESPACE_DEFAULT"


class SpecProvisioningResultData(BaseModel):
    """Provisioning result data."""

    model_config = ConfigDict(
        extra="allow"
    )  # Allow unknown fields for forward compatibility

    provisioning_result_uuid: str = Field(
        ..., description="UUID of the provisioning result"
    )
    exit_code: int | None = Field(None, description="Provisioning exit code")
    error: str | None = Field(None, description="Provisioning error message")
    automated_scan_parameters_config: dict[str, Any] | None = Field(
        None, description="Automated scan parameter configuration"
    )
    auto_detect_result: dict[str, Any] | None = Field(
        None, description="Auto detect results"
    )
    tool_chains_source: str | None = Field(
        None, description="Toolchain source (enum: TOOL_CHAINS_SOURCE_*)"
    )
    tool_chains: dict[str, Any] | None = Field(None, description="Toolchains installed")
    scan_profile: dict[str, Any] | None = Field(
        None, description="Scan profile used for provisioning"
    )


class Version(BaseModel):
    """Version information for a ref."""

    ref: str = Field(..., description="Resolved ref (tag, branch, or SHA)")
    sha: str | None = Field(None, description="SHA of the source control version")
    metadata: dict[str, str] | None = Field(None, description="Version metadata")


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
    start_time: str | None = Field(
        None,
        description="Time the scan started",
        json_schema_extra={"format": "date-time"},
    )
    end_time: str | None = Field(
        None,
        description="Time the scan ended",
        json_schema_extra={"format": "date-time"},
    )
    stats: dict[str, int] | None = Field(
        None,
        description="Map of stats such as how many issues were ingested "
        "during the scan.",
    )
    refs: list[str] | None = Field(None, description="List of branches scanned")
    environment: Environment | None = Field(
        None,
        description="All the information available about the input "
        "parameters and the host environment.",
    )
    has_panic: bool | None = Field(
        None, description="True if there was a panic during the scan"
    )
    exit_code: EndorctlRC | None = Field(None, description="The exit code of the scan")
    logs: list[str] | None = Field(
        None, description="User facing log output for the scan"
    )
    policies_triggered: list[str] | None = Field(
        None, description="List of policy uuids triggered during the scan"
    )
    warning_findings: list[str] | None = Field(
        None, description="List of warning finding uuids identified by the scan"
    )
    blocking_findings: list[str] | None = Field(
        None, description="List of blocking finding uuids identified by the scan"
    )
    runtimes: dict[str, int] | None = Field(
        None,
        description="A map of internal scan type runtimes (in milliseconds) "
        "indexed by internal scan type string.",
    )
    findings: list[str] | None = Field(
        None, description="List of all finding UUIDs identified by the scan"
    )
    deleted_findings: dict[str, SpecFindingData] | None = Field(
        None,
        description="Map of basic metadata for all findings deleted by the "
        "scan, indexed by finding uuid. Not available for CI runs.",
    )
    languages_detected: list[str] | None = Field(
        None, description="List of languages detected by the scan"
    )
    provisioning_result_uuid: str | None = Field(
        None, description="UUID of the provisioning result"
    )
    versions: list[Version] | None = Field(
        None, description="Version information for each ref"
    )
    ecosystem_pkg_counts: dict[str, int] | None = Field(
        None,
        description="Number of package versions per ecosystems processed "
        "during the scan.",
    )
    ecosystem_dep_counts: dict[str, int] | None = Field(
        None,
        description="Number of dependencies per ecosystems processed during the scan.",
    )
    provisioning_result: SpecProvisioningResultData | None = Field(
        None, description="Provisioning result data"
    )

    # Deprecated fields (kept for backward compatibility)
    errors: list[str] | None = Field(None, description="Deprecated. Use logs instead.")
    warnings: list[str] | None = Field(
        None, description="Deprecated. Use logs instead."
    )
    infos: list[str] | None = Field(None, description="Deprecated. Use logs instead.")
    all_findings: dict[str, SpecFindingData] | None = Field(
        None, description="Deprecated."
    )
    exception_findings: dict[str, SpecFindingData] | None = Field(
        None, description="Deprecated."
    )


class ScanResult(BaseResource):
    """An Endor Labs ScanResult entity extending BaseResource.

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
    # spec and context optional when API returns partial body (e.g. after update)
    spec: ScanResultSpec | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Scan result specification"
    )
    context: Context | None = Field(
        None,
        description="Context information for the scan result",
        alias="context",
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data: Any) -> None:
        # Convert spec to ScanResultSpec if present (partial response may omit spec)
        spec_val = data.get("spec")
        if spec_val is not None and isinstance(spec_val, dict):
            data["spec"] = ScanResultSpec(**spec_val)
        super().__init__(**data)

    @override
    @classmethod
    def get_mutable_fields_cls(cls) -> list[str]:
        """Get list of mutable fields for ScanResult."""
        return ["meta.name", "meta.description", "meta.tags", "spec"]


class ScanResultMetaCreate(BaseModel):
    """Metadata for creating a ScanResult."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="The name of the scan result"
    )
    description: str | None = Field(None, description="Description of the scan result")


class ScanResultSpecCreate(BaseModel):
    """Specification for creating a ScanResult."""

    status: ScanResultSpecStatus = Field(..., description="Scan status")
    type: ScanResultSpecType = Field(..., description="Scan type")
    start_time: str | None = Field(None, description="Scan start time")
    end_time: str | None = Field(None, description="Scan end time")
    environment: Environment | None = Field(None, description="Environment info")


class CreateScanResultPayload(BaseModel):
    """Payload for creating a new ScanResult."""

    meta: ScanResultMetaCreate
    spec: ScanResultSpecCreate
    context: Context


def build_create_payload(**kwargs: Any) -> CreateScanResultPayload:
    """Build CreateScanResultPayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateScanResultPayload, kwargs, attr_name="ScanResult"
    )


class ScanResultMetaUpdate(BaseModel):
    """Metadata for updating a ScanResult."""

    description: str | None = Field(
        None, description="Updated description of the scan result"
    )
    tags: list[str] | None = Field(None, description="Updated tags for the scan result")
    annotations: dict[str, Any] | None = Field(
        None, description="Updated annotations for the scan result"
    )


class ScanResultSpecUpdate(BaseModel):
    """Specification for updating a ScanResult.

    Note: Most spec fields are system-generated and cannot be updated.
    This model exists for completeness but most fields are omitted.
    """

    pass  # No updatable spec fields identified


class UpdateScanResultPayload(BaseModel):
    """Payload for updating an Endor Labs ScanResult.

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

    meta: ScanResultMetaUpdate | None = Field(
        None, description="Updated scan result metadata"
    )
    spec: ScanResultSpecUpdate | None = Field(
        None, description="Updated scan result specification"
    )
    context: Context | None = Field(None, description="Updated scan result context")
