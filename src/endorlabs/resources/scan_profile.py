"""ScanProfile — thin consumer wrapper over generated V1ScanProfile."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from endorlabs.generated.models.provisioning_result_service import V1ScanProfile

from .base import FlexibleEnum
from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class ScanProfile(V1ScanProfile, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for ScanProfile (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("ScanProfile")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("ScanProfile")


# --- integration / create-update compat (pre-cutover helpers) ---


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


def build_create_payload(**kwargs: Any) -> CreateScanProfilePayload:
    """Build CreateScanProfilePayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateScanProfilePayload, kwargs, attr_name="ScanProfile"
    )
