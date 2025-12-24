"""
ScanProfile resource module for Endor Labs API.

This module provides CRUD operations for ScanProfile resources following the
established patterns from the Project and Finding resource implementations.

API OPERATIONS SUPPORTED:
- GET: List scan profiles, Get scan profile by UUID
- POST: Create scan profile
- PATCH: Update scan profile
- DELETE: Delete scan profile

API USAGE NOTES:
- ScanProfiles define scan configuration including toolchains and scan parameters
- ScanProfiles can be set as default for a namespace
- ScanProfiles support propagation to child namespaces via propagate field
- For more information, see the ScanProfileService REST API documentation
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
    FlexibleEnum,
)
from ..types import ListParameters

logger = logging.getLogger(__name__)


def _get_scan_profile_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for scan profiles."""
    return BaseResourceOperations(client, "scan-profiles", ScanProfile)


class AISastAnalysisMode(FlexibleEnum):
    """AI SAST analysis mode enumeration."""

    UNSPECIFIED = "AISAST_ANALYSIS_MODE_UNSPECIFIED"
    AUTO = "AISAST_ANALYSIS_MODE_AUTO"
    MANUAL = "AISAST_ANALYSIS_MODE_MANUAL"


class AutomatedScanParametersBazelConfiguration(BaseModel):
    """Bazel configuration for automated scans."""

    bazel_workspace_path: Optional[str] = Field(
        None, description="Bazel workspace path"
    )
    bazel_include_targets: Optional[List[str]] = Field(
        None, description="Bazel targets to include"
    )
    bazel_exclude_targets: Optional[List[str]] = Field(
        None, description="Bazel targets to exclude"
    )
    bazel_show_internal_targets: Optional[bool] = Field(
        None, description="Show internal Bazel targets"
    )
    bazel_targets_query: Optional[str] = Field(
        None, description="Bazel targets query"
    )


class AutomatedScanParameters(BaseModel):
    """Automated scan parameters configuration."""

    model_config = ConfigDict(extra="allow")  # Allow unknown fields for forward compatibility

    full_pr_scan: Optional[bool] = Field(
        None, description="Enable full scan during PRs"
    )
    full_push_scan: Optional[bool] = Field(
        None, description="Enable full scan during pushes"
    )
    included_paths: Optional[List[str]] = Field(
        None, description="Paths to include in scan"
    )
    excluded_paths: Optional[List[str]] = Field(
        None, description="Paths to exclude from scan"
    )
    languages: Optional[List[str]] = Field(
        None, description="Languages to scan (empty = defaults)"
    )
    call_graph_languages: Optional[List[str]] = Field(
        None, description="Languages for call graph calculation"
    )
    bazel_configuration: Optional[AutomatedScanParametersBazelConfiguration] = (
        Field(None, description="Bazel build configuration")
    )
    additional_environment_variables: Optional[List[str]] = Field(
        None, description="Additional environment variables"
    )
    enable_pr_comments: Optional[bool] = Field(
        None, description="Enable PR comments"
    )
    enable_remediation_action: Optional[bool] = Field(
        None, description="Enable remediation actions"
    )
    enable_automated_pr_scans: Optional[bool] = Field(
        None, description="Enable automated PR scans"
    )
    enable_sast_scan: Optional[bool] = Field(None, description="Enable SAST scan")
    enable_secret_scan: Optional[bool] = Field(
        None, description="Enable secret scan"
    )
    enable_full_git_log_secret_scan: Optional[bool] = Field(
        None, description="Enable full git log secret scan"
    )
    disable_code_storage: Optional[bool] = Field(
        None, description="Disable code storage"
    )
    disable_code_snippet_storage: Optional[bool] = Field(
        None, description="Disable code snippet storage"
    )
    enable_pr_security_review_scan: Optional[bool] = Field(
        None, description="Enable PR security review scan"
    )
    enable_pr_incremental_scan: Optional[bool] = Field(
        None, description="Enable PR incremental scan"
    )
    enable_ai_sast_scan: Optional[bool] = Field(
        None, description="Enable AI SAST scan"
    )


class RemediationParametersAutomatedPRParameters(BaseModel):
    """Parameters for automated pull requests."""

    # Using Dict[str, Any] for flexibility as structure may vary
    pass  # Structure not fully defined in OpenAPI spec


class RemediationParameters(BaseModel):
    """Remediation parameters configuration."""

    model_config = ConfigDict(extra="allow")  # Allow unknown fields for forward compatibility

    automated_pr_parameters: Optional[RemediationParametersAutomatedPRParameters] = (
        Field(None, description="Automated PR parameters")
    )


class SecurityReviewScannerParameters(BaseModel):
    """Security review scanner parameters."""

    model_config = ConfigDict(extra="allow")  # Allow unknown fields for forward compatibility

    user_prompt: Optional[str] = Field(
        None, description="User prompt for security review scanner"
    )
    disable_code_summary: Optional[bool] = Field(
        None, description="Disable code summary in security review"
    )


class ExporterParameters(BaseModel):
    """Exporter parameters configuration."""

    model_config = ConfigDict(extra="allow")  # Allow unknown fields for forward compatibility

    exporter_uuids: Optional[List[str]] = Field(
        None, description="List of exporter UUIDs"
    )


class AISastAnalysisParameters(BaseModel):
    """AI SAST analysis parameters."""

    model_config = ConfigDict(extra="allow")  # Allow unknown fields for forward compatibility

    retriage: Optional[bool] = Field(
        None, description="Enable retriage of SAST findings using AI"
    )
    mode: Optional[AISastAnalysisMode] = Field(
        None, description="Mode for AI SAST analysis triage"
    )


class ScanProfileMeta(BaseMeta):
    """Scan profile metadata extending BaseMeta."""

    # ScanProfile-specific fields only (universal fields inherited from BaseMeta)
    pass  # No additional fields needed, all were universal


class ScanProfileSpec(BaseSpec):
    """Scan profile specification extending BaseSpec.

    Field Mutability Guide:
    ======================

    FIELD MUTABILITY (per OpenAPI spec):
    =====================================
    MUTABLE FIELDS:
    - toolchain_profile: Toolchain configuration (can be updated)
    - automated_scan_parameters: Scan parameters (can be updated)
    - remediation_parameters: Remediation settings (can be updated)
    - is_default: Default profile flag (can be updated)
    - security_review_scanner_parameters: Security review settings
    - exporter_parameters: Exporter settings
    - ai_sast_analysis_parameters: AI SAST analysis settings

    Note: All spec fields are mutable and can be updated via PATCH.
    """

    # Optional fields (all are optional per OpenAPI spec)
    toolchain_profile: Optional[Dict[str, Any]] = Field(
        None,
        description="OS/architecture-specific toolchain configuration. "
        "Structure: os -> arch -> toolchains (e.g., java_tool_chain, "
        "python_tool_chain).",
    )
    automated_scan_parameters: Optional[AutomatedScanParameters] = Field(
        None,
        description="Parameters applied during cloud scans by Endor Labs",
    )
    remediation_parameters: Optional[RemediationParameters] = Field(
        None, description="Parameters required for remediation actions"
    )
    is_default: Optional[bool] = Field(
        None, description="Indicates this is the namespace default profile"
    )
    security_review_scanner_parameters: Optional[
        SecurityReviewScannerParameters
    ] = Field(
        None, description="Parameters for security review scanner"
    )
    exporter_parameters: Optional[ExporterParameters] = Field(
        None, description="Parameters for exporter"
    )
    ai_sast_analysis_parameters: Optional[AISastAnalysisParameters] = Field(
        None, description="Parameters for AI SAST analysis workflow"
    )


class ScanProfile(BaseResource):
    """
    An Endor Labs ScanProfile entity extending BaseResource.

    ScanProfile-specific fields (universal fields inherited from BaseResource).

    OPERATION SUPPORT:
    ==================
    ✅ GET: List scan profiles, Get by UUID
    ✅ POST: Create scan profile
    ✅ PATCH: Update scan profile
    ✅ DELETE: Delete scan profile

    FIELD MUTABILITY:
    =================
    IMMUTABLE FIELDS (readOnly: true in API spec):
    - uuid: Unique identifier (readOnly: true)
    - meta.create_time, meta.update_time, meta.upsert_time: Timestamps
    - meta.kind, meta.version: Resource metadata
    - meta.created_by, meta.updated_by: Audit fields
    - meta.references, meta.index_data: System-managed fields
    - tenant_meta.namespace: Namespace assignment

    MUTABLE FIELDS:
    - meta.name, meta.description, meta.tags: Metadata
    - meta.annotations: Resource annotations
    - spec.*: All spec fields are mutable
    - propagate: Namespace visibility flag
    """

    # ScanProfile-specific fields (universal fields inherited from BaseResource)
    spec: ScanProfileSpec = Field(..., description="Scan profile specification")  # type: ignore
    propagate: Optional[bool] = Field(
        None,
        description="Indicates object should be visible in child namespaces",
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data):
        # Convert spec to ScanProfileSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = ScanProfileSpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Skip drift detection for typed nested models - they handle their own validation
            # These will be converted to Pydantic models by the field validators
            typed_model_fields = {
                "automated_scan_parameters",  # AutomatedScanParameters
                "remediation_parameters",  # RemediationParameters
                "security_review_scanner_parameters",  # SecurityReviewScannerParameters
                "exporter_parameters",  # ExporterParameters
                "ai_sast_analysis_parameters",  # AISastAnalysisParameters
            }
            
            # Known top-level fields in ScanProfileSpec
            known_fields = {
                "toolchain_profile",  # Dict[str, Any] - flexible structure
                "automated_scan_parameters",  # Typed model
                "remediation_parameters",  # Typed model
                "is_default",
                "security_review_scanner_parameters",  # Typed model
                "exporter_parameters",  # Typed model
                "ai_sast_analysis_parameters",  # Typed model
            }
            
            # Only check top-level fields, skip nested model fields
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v


class ScanProfileMetaCreate(BaseModel):
    """Metadata for creating a ScanProfile."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="The name of the scan profile"
    )
    description: Optional[str] = Field(
        None, description="Description of the scan profile"
    )


class ScanProfileSpecCreate(BaseModel):
    """Specification for creating a ScanProfile."""

    toolchain_profile: Optional[Dict[str, Any]] = Field(
        None, description="Toolchain profile configuration"
    )
    automated_scan_parameters: Optional[AutomatedScanParameters] = Field(
        None, description="Automated scan parameters"
    )
    remediation_parameters: Optional[RemediationParameters] = Field(
        None, description="Remediation parameters"
    )
    is_default: Optional[bool] = Field(
        None, description="Set as default profile"
    )
    security_review_scanner_parameters: Optional[
        SecurityReviewScannerParameters
    ] = Field(None, description="Security review scanner parameters")
    exporter_parameters: Optional[ExporterParameters] = Field(
        None, description="Exporter parameters"
    )
    ai_sast_analysis_parameters: Optional[AISastAnalysisParameters] = Field(
        None, description="AI SAST analysis parameters"
    )


class CreateScanProfilePayload(BaseModel):
    """Payload for creating a new ScanProfile."""

    meta: ScanProfileMetaCreate
    spec: ScanProfileSpecCreate
    propagate: Optional[bool] = Field(
        None, description="Make visible in child namespaces"
    )


class ScanProfileMetaUpdate(BaseModel):
    """Metadata for updating a ScanProfile."""

    description: Optional[str] = Field(
        None, description="Updated description of the scan profile"
    )
    tags: Optional[List[str]] = Field(
        None, description="Updated tags for the scan profile"
    )
    annotations: Optional[Dict[str, Any]] = Field(
        None, description="Updated annotations for the scan profile"
    )


class ScanProfileSpecUpdate(BaseModel):
    """Specification for updating a ScanProfile."""

    toolchain_profile: Optional[Dict[str, Any]] = Field(
        None, description="Updated toolchain profile configuration"
    )
    automated_scan_parameters: Optional[AutomatedScanParameters] = Field(
        None, description="Updated automated scan parameters"
    )
    remediation_parameters: Optional[RemediationParameters] = Field(
        None, description="Updated remediation parameters"
    )
    is_default: Optional[bool] = Field(
        None, description="Updated default profile flag"
    )
    security_review_scanner_parameters: Optional[
        SecurityReviewScannerParameters
    ] = Field(None, description="Updated security review scanner parameters")
    exporter_parameters: Optional[ExporterParameters] = Field(
        None, description="Updated exporter parameters"
    )
    ai_sast_analysis_parameters: Optional[AISastAnalysisParameters] = Field(
        None, description="Updated AI SAST analysis parameters"
    )


class UpdateScanProfilePayload(BaseModel):
    """
    Payload for updating an Endor Labs ScanProfile.

    MUTABLE FIELDS (can be updated via PATCH):
    - meta.tags: General resource tags
    - meta.description: Resource description
    - meta.annotations: Resource annotations
    - spec.*: All spec fields are mutable
    - propagate: Namespace visibility flag

    IMMUTABLE FIELDS (read-only, managed by API):
    - uuid: Unique identifier (readOnly: true)
    - meta.name: Scan profile name (set at creation)
    - meta.create_time, meta.update_time, meta.upsert_time: Timestamps
    - meta.kind, meta.version: Resource metadata
    - meta.created_by, meta.updated_by: Audit fields
    - meta.references, meta.index_data: System-managed fields
    - tenant_meta.namespace: Namespace assignment

    Example:
        >>> payload = UpdateScanProfilePayload(
        ...     spec=ScanProfileSpecUpdate(is_default=True)
        ... )
        >>> scan_profile = update_scan_profile(
        ...     client, namespace, uuid, payload, "spec.is_default"
        ... )
    """

    meta: Optional[ScanProfileMetaUpdate] = Field(
        None, description="Updated scan profile metadata"
    )
    spec: Optional[ScanProfileSpecUpdate] = Field(
        None, description="Updated scan profile specification"
    )
    propagate: Optional[bool] = Field(
        None, description="Updated namespace visibility flag"
    )


def list_scan_profiles(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
) -> List[ScanProfile]:
    """
    List scan profiles in a namespace.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name (e.g., 'tenant.namespace')
        list_params: Optional list parameters for filtering, pagination, etc.

    Returns:
        List of ScanProfile objects
    """
    ops = _get_scan_profile_ops(client)
    return ops.list(tenant_meta_namespace, list_params)  # type: ignore


def get_scan_profile(
    client: APIClient, tenant_meta_namespace: str, scan_profile_uuid: str
) -> Optional[ScanProfile]:
    """
    Get a specific scan profile by UUID.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        scan_profile_uuid: UUID of the scan profile to retrieve

    Returns:
        ScanProfile object if found, None otherwise
    """
    ops = _get_scan_profile_ops(client)
    return ops.get(tenant_meta_namespace, scan_profile_uuid)  # type: ignore


def create_scan_profile(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateScanProfilePayload,
) -> Optional[ScanProfile]:
    """
    Create a new scan profile.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        payload: ScanProfile creation payload

    Returns:
        Created ScanProfile object if successful, None otherwise
    """
    url = f"v1/namespaces/{tenant_meta_namespace}/scan-profiles"

    try:
        response = client.post(url, json=payload.model_dump())
        if response:
            data = response.json()
            return ScanProfile(**data)
        return None
    except Exception as e:
        logger.error(f"Error creating scan profile: {e}")
        return None


def update_scan_profile(
    client: APIClient,
    tenant_meta_namespace: str,
    scan_profile_uuid: str,
    payload: UpdateScanProfilePayload,
    update_mask: Optional[str] = None,
) -> Optional[ScanProfile]:
    """
    Update an existing scan profile using partial updates.

    This function supports updating only specific fields using the update_mask
    parameter, which enables efficient partial updates without overwriting
    unchanged fields.

    MUTABLE FIELDS:
    - meta.tags: General resource tags
    - meta.description: Resource description
    - meta.annotations: Resource annotations
    - spec.*: All spec fields are mutable
    - propagate: Namespace visibility flag

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        scan_profile_uuid: UUID of the scan profile to update
        payload: ScanProfile update payload
        update_mask: Optional comma-separated list of fields to update
            (e.g., "spec.is_default,propagate"). If provided, only these
            fields will be updated. If omitted, all non-None fields in
            payload will be updated.

    Returns:
        Updated ScanProfile object if successful, None otherwise

    Raises:
        requests.exceptions.HTTPError: For API-level errors (403, 404, etc.)
        pydantic.ValidationError: If response data doesn't match expected schema

    Example:
        >>> # Update scan profile to set as default
        >>> payload = UpdateScanProfilePayload(
        ...     spec=ScanProfileSpecUpdate(is_default=True)
        ... )
        >>> scan_profile = update_scan_profile(
        ...     client, namespace, uuid, payload, "spec.is_default"
        ... )
    """
    url = f"v1/namespaces/{tenant_meta_namespace}/scan-profiles"

    try:
        # Build update request body
        update_data = {
            "object": {
                "uuid": scan_profile_uuid,
                **payload.model_dump(exclude_none=True),
            }
        }

        # Add update mask if provided
        if update_mask:
            update_data["request"] = {"update_mask": update_mask}

        response = client.patch(url, json=update_data)
        if response:
            data = response.json()
            return ScanProfile(**data)
        return None
    except Exception as e:
        logger.error(f"Error updating scan profile: {e}")
        return None


def delete_scan_profile(
    client: APIClient, tenant_meta_namespace: str, scan_profile_uuid: str
) -> bool:
    """
    Delete a scan profile.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        scan_profile_uuid: UUID of the scan profile to delete

    Returns:
        True if deletion was successful, False otherwise
    """
    ops = _get_scan_profile_ops(client)
    return ops.delete(tenant_meta_namespace, scan_profile_uuid)

