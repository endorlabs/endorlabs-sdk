"""ScanProfile resource module for Endor Labs API.

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

from __future__ import annotations

from typing import Any, override

from pydantic import BaseModel, ConfigDict, Field

from ..utils.logging_config import get_resource_logger
from .base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
    FlexibleEnum,
)

logger = get_resource_logger(__name__)


class AISastAnalysisMode(FlexibleEnum):
    """AI SAST analysis mode enumeration."""

    UNSPECIFIED = "AISAST_ANALYSIS_MODE_UNSPECIFIED"
    AUTO = "AISAST_ANALYSIS_MODE_AUTO"
    MANUAL = "AISAST_ANALYSIS_MODE_MANUAL"


class AutomatedScanParametersBazelConfiguration(BaseModel):
    """Bazel configuration for automated scans."""

    bazel_workspace_path: str | None = Field(None, description="Bazel workspace path")
    bazel_include_targets: list[str] | None = Field(
        None, description="Bazel targets to include"
    )
    bazel_exclude_targets: list[str] | None = Field(
        None, description="Bazel targets to exclude"
    )
    bazel_show_internal_targets: bool | None = Field(
        None, description="Show internal Bazel targets"
    )
    bazel_targets_query: str | None = Field(None, description="Bazel targets query")


class AutomatedScanParameters(BaseModel):
    """Automated scan parameters configuration."""

    model_config = ConfigDict(
        extra="allow"
    )  # Allow unknown fields for forward compatibility

    full_pr_scan: bool | None = Field(None, description="Enable full scan during PRs")
    full_push_scan: bool | None = Field(
        None, description="Enable full scan during pushes"
    )
    included_paths: list[str] | None = Field(
        None, description="Paths to include in scan"
    )
    excluded_paths: list[str] | None = Field(
        None, description="Paths to exclude from scan"
    )
    languages: list[str] | None = Field(
        None, description="Languages to scan (empty = defaults)"
    )
    call_graph_languages: list[str] | None = Field(
        None, description="Languages for call graph calculation"
    )
    bazel_configuration: AutomatedScanParametersBazelConfiguration | None = Field(
        None, description="Bazel build configuration"
    )
    additional_environment_variables: list[str] | None = Field(
        None, description="Additional environment variables"
    )
    enable_pr_comments: bool | None = Field(None, description="Enable PR comments")
    enable_remediation_action: bool | None = Field(
        None, description="Enable remediation actions"
    )
    enable_automated_pr_scans: bool | None = Field(
        None, description="Enable automated PR scans"
    )
    enable_sast_scan: bool | None = Field(None, description="Enable SAST scan")
    enable_secret_scan: bool | None = Field(None, description="Enable secret scan")
    enable_full_git_log_secret_scan: bool | None = Field(
        None, description="Enable full git log secret scan"
    )
    disable_code_storage: bool | None = Field(None, description="Disable code storage")
    disable_code_snippet_storage: bool | None = Field(
        None, description="Disable code snippet storage"
    )
    enable_pr_security_review_scan: bool | None = Field(
        None, description="Enable PR security review scan"
    )
    enable_pr_incremental_scan: bool | None = Field(
        None, description="Enable PR incremental scan"
    )
    enable_ai_sast_scan: bool | None = Field(None, description="Enable AI SAST scan")


class RemediationParametersAutomatedPRParameters(BaseModel):
    """Parameters for automated pull requests."""

    # Using Dict[str, Any] for flexibility as structure may vary
    pass  # Structure not fully defined in OpenAPI spec


class RemediationParameters(BaseModel):
    """Remediation parameters configuration."""

    model_config = ConfigDict(
        extra="allow"
    )  # Allow unknown fields for forward compatibility

    automated_pr_parameters: RemediationParametersAutomatedPRParameters | None = Field(
        None, description="Automated PR parameters"
    )


class SecurityReviewScannerParameters(BaseModel):
    """Security review scanner parameters."""

    model_config = ConfigDict(
        extra="allow"
    )  # Allow unknown fields for forward compatibility

    user_prompt: str | None = Field(
        None, description="User prompt for security review scanner"
    )
    disable_code_summary: bool | None = Field(
        None, description="Disable code summary in security review"
    )


class ExporterParameters(BaseModel):
    """Exporter parameters configuration."""

    model_config = ConfigDict(
        extra="allow"
    )  # Allow unknown fields for forward compatibility

    exporter_uuids: list[str] | None = Field(None, description="List of exporter UUIDs")


class AISastAnalysisParameters(BaseModel):
    """AI SAST analysis parameters."""

    model_config = ConfigDict(
        extra="allow"
    )  # Allow unknown fields for forward compatibility

    retriage: bool | None = Field(
        None, description="Enable retriage of SAST findings using AI"
    )
    mode: AISastAnalysisMode | None = Field(
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
    toolchain_profile: dict[str, Any] | None = Field(
        None,
        description="OS/architecture-specific toolchain configuration. "
        "Structure: os -> arch -> toolchains (e.g., java_tool_chain, "
        "python_tool_chain).",
    )
    automated_scan_parameters: AutomatedScanParameters | None = Field(
        None,
        description="Parameters applied during cloud scans by Endor Labs",
    )
    remediation_parameters: RemediationParameters | None = Field(
        None, description="Parameters required for remediation actions"
    )
    is_default: bool | None = Field(
        None, description="Indicates this is the namespace default profile"
    )
    security_review_scanner_parameters: SecurityReviewScannerParameters | None = Field(
        None, description="Parameters for security review scanner"
    )
    exporter_parameters: ExporterParameters | None = Field(
        None, description="Parameters for exporter"
    )
    ai_sast_analysis_parameters: AISastAnalysisParameters | None = Field(
        None, description="Parameters for AI SAST analysis workflow"
    )


class ScanProfile(BaseResource):
    """An Endor Labs ScanProfile entity extending BaseResource.

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
    # spec optional on response when API returns partial body (e.g. after update)
    spec: ScanProfileSpec | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Scan profile specification"
    )
    propagate: bool | None = Field(
        None,
        description="Indicates object should be visible in child namespaces",
    )

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data: Any) -> None:
        # Convert spec to ScanProfileSpec if present (partial response may omit spec)
        spec_val = data.get("spec")
        if spec_val is not None and isinstance(spec_val, dict):
            data["spec"] = ScanProfileSpec(**spec_val)
        super().__init__(**data)

    @override
    @classmethod
    def get_mutable_fields_cls(cls) -> list[str]:
        """Get list of mutable fields for ScanProfile."""
        return ["meta.name", "meta.description", "meta.tags", "spec"]


class ScanProfileMetaCreate(BaseModel):
    """Metadata for creating a ScanProfile."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="The name of the scan profile"
    )
    description: str | None = Field(None, description="Description of the scan profile")


class ScanProfileSpecCreate(BaseModel):
    """Specification for creating a ScanProfile."""

    toolchain_profile: dict[str, Any] | None = Field(
        None, description="Toolchain profile configuration"
    )
    automated_scan_parameters: AutomatedScanParameters | None = Field(
        None, description="Automated scan parameters"
    )
    remediation_parameters: RemediationParameters | None = Field(
        None, description="Remediation parameters"
    )
    is_default: bool | None = Field(None, description="Set as default profile")
    security_review_scanner_parameters: SecurityReviewScannerParameters | None = Field(
        None, description="Security review scanner parameters"
    )
    exporter_parameters: ExporterParameters | None = Field(
        None, description="Exporter parameters"
    )
    ai_sast_analysis_parameters: AISastAnalysisParameters | None = Field(
        None, description="AI SAST analysis parameters"
    )


class CreateScanProfilePayload(BaseModel):
    """Payload for creating a new ScanProfile."""

    meta: ScanProfileMetaCreate
    spec: ScanProfileSpecCreate
    propagate: bool | None = Field(None, description="Make visible in child namespaces")


def build_create_payload(
    *,
    name: str,
    description: str | None = None,
    is_default: bool | None = None,
    propagate: bool | None = None,
    **spec_kwargs: Any,
) -> CreateScanProfilePayload:
    """Build CreateScanProfilePayload from kwargs (decoupled facade create).

    Required: name.
    Optional: description, is_default, propagate, and any spec fields
    (e.g. automated_scan_parameters, toolchain_profile) passed as spec_kwargs.
    """
    meta = ScanProfileMetaCreate(name=name, description=description)
    spec = ScanProfileSpecCreate(is_default=is_default, **spec_kwargs)
    return CreateScanProfilePayload(meta=meta, spec=spec, propagate=propagate)


class ScanProfileMetaUpdate(BaseModel):
    """Metadata for updating a ScanProfile."""

    description: str | None = Field(
        None, description="Updated description of the scan profile"
    )
    tags: list[str] | None = Field(
        None, description="Updated tags for the scan profile"
    )
    annotations: dict[str, Any] | None = Field(
        None, description="Updated annotations for the scan profile"
    )


class ScanProfileSpecUpdate(BaseModel):
    """Specification for updating a ScanProfile."""

    toolchain_profile: dict[str, Any] | None = Field(
        None, description="Updated toolchain profile configuration"
    )
    automated_scan_parameters: AutomatedScanParameters | None = Field(
        None, description="Updated automated scan parameters"
    )
    remediation_parameters: RemediationParameters | None = Field(
        None, description="Updated remediation parameters"
    )
    is_default: bool | None = Field(None, description="Updated default profile flag")
    security_review_scanner_parameters: SecurityReviewScannerParameters | None = Field(
        None, description="Updated security review scanner parameters"
    )
    exporter_parameters: ExporterParameters | None = Field(
        None, description="Updated exporter parameters"
    )
    ai_sast_analysis_parameters: AISastAnalysisParameters | None = Field(
        None, description="Updated AI SAST analysis parameters"
    )


class UpdateScanProfilePayload(BaseModel):
    """Payload for updating an Endor Labs ScanProfile.

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

    meta: ScanProfileMetaUpdate | None = Field(
        None, description="Updated scan profile metadata"
    )
    spec: ScanProfileSpecUpdate | None = Field(
        None, description="Updated scan profile specification"
    )
    propagate: bool | None = Field(
        None, description="Updated namespace visibility flag"
    )
