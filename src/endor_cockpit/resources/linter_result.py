"""LinterResult resource module for Endor Labs API.

This module provides CRUD operations for LinterResult resources following the
established patterns from the base class implementation.

**INTERMEDIATE RESOURCE (IR) - Debugging Value:**

LinterResult is an intermediate resource that sits between scan execution and
Finding generation. It's primarily useful for debugging and troubleshooting
the scan → finding pipeline.

**When to Use LinterResult vs Finding:**

- **Use Finding** for normal operations (most users should use this)
- **Use LinterResult** for debugging when you need:
  - Full SARIF output with structured locations and code flows
  - Scan execution context (Git reference, version, ecosystem at scan time)
  - Code fingerprints for deduplication analysis
  - Correctness analysis results (taint analysis, reachability)
  - Understanding severity transformations (rule → scan → finding)
  - Tracing scan results that didn't become findings

**Key Debugging Value:**

1. **Full SARIF Output**: Complete scan results with structured locations,
   code snippets, and code flows (data flow analysis)
2. **Scan Context**: Git reference, version, ecosystem preserved at scan time
3. **Fingerprints**: Code fingerprints used for deduplication logic
4. **Correctness Analysis**: Taint analysis and reachability results
5. **Severity Tracking**: See intermediate severity after rule evaluation
   but before finding generation

**Note**: Most rule metadata (rule_uuid, message, CWEs, etc.) is also
available in Finding.finding_metadata.custom, but LinterResult provides
the raw scan output and execution context that's lost in Finding.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseResourceOperations,
    BaseSpec,
    FlexibleEnum,
)
from ..types import ListParameters

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


class LinterResultOrigin(FlexibleEnum):
    """Linter result origin enumeration."""

    UNSPECIFIED = "LINTER_RESULT_ORIGIN_UNSPECIFIED"
    SEMGREP = "LINTER_RESULT_ORIGIN_SEMGREP"
    SECRETS_SCANNER = "LINTER_RESULT_ORIGIN_SECRETS_SCANNER"
    SAST_SCANNER = "LINTER_RESULT_ORIGIN_SAST_SCANNER"
    LLM_SCANNER = "LINTER_RESULT_ORIGIN_LLM_SCANNER"
    AI_SAST_SCANNER = "LINTER_RESULT_ORIGIN_AI_SAST_SCANNER"


class LinterResultLevel(FlexibleEnum):
    """Linter result level enumeration."""

    UNSPECIFIED = "LINTER_RESULT_LEVEL_UNSPECIFIED"
    ERROR = "LINTER_RESULT_LEVEL_ERROR"
    WARNING = "LINTER_RESULT_LEVEL_WARNING"
    INFO = "LINTER_RESULT_LEVEL_INFO"
    DEBUG = "LINTER_RESULT_LEVEL_DEBUG"


class DistributionFormatType(FlexibleEnum):
    """Distribution format type enumeration."""

    UNSPECIFIED = "DISTRIBUTION_FORMAT_TYPE_UNSPECIFIED"
    PYTHON_EGG = "DISTRIBUTION_FORMAT_TYPE_PYTHON_EGG"
    PYTHON_SOURCE = "DISTRIBUTION_FORMAT_TYPE_PYTHON_SOURCE"
    PYTHON_WHEEL = "DISTRIBUTION_FORMAT_TYPE_PYTHON_WHEEL"


class Ecosystem(FlexibleEnum):
    """Ecosystem enumeration."""

    UNSPECIFIED = "ECOSYSTEM_UNSPECIFIED"
    AI_MODEL = "ECOSYSTEM_AI_MODEL"
    APK = "ECOSYSTEM_APK"
    C = "ECOSYSTEM_C"
    CARGO = "ECOSYSTEM_CARGO"
    COCOAPOD = "ECOSYSTEM_COCOAPOD"
    CONTAINER = "ECOSYSTEM_CONTAINER"
    DEBIAN = "ECOSYSTEM_DEBIAN"
    GEM = "ECOSYSTEM_GEM"
    GIT = "ECOSYSTEM_GIT"
    GITHUB_ACTION = "ECOSYSTEM_GITHUB_ACTION"
    GO = "ECOSYSTEM_GO"
    HUGGING_FACE = "ECOSYSTEM_HUGGING_FACE"
    MAVEN = "ECOSYSTEM_MAVEN"
    NPM = "ECOSYSTEM_NPM"
    NUGET = "ECOSYSTEM_NUGET"
    PACKAGIST = "ECOSYSTEM_PACKAGIST"
    PYPI = "ECOSYSTEM_PYPI"
    RPM = "ECOSYSTEM_RPM"
    SBOM = "ECOSYSTEM_SBOM"
    SWIFT = "ECOSYSTEM_SWIFT"


class SarifText(BaseModel):
    """SARIF text object with text and markdown fields."""

    text: str | None = Field(None, description="The actual text content")
    markdown: str | None = Field(
        None, description="Markdown representation of the content"
    )


class SarifResult(BaseModel):
    """SARIF result for linter."""

    rule_id: str | None = Field(None, description="Rule ID")
    message: SarifText | None = Field(None, description="Result message")
    level: str | None = Field(None, description="Result level")
    locations: list[dict[str, Any]] | None = Field(None, description="Result locations")
    fingerprints: dict[str, Any] | None = Field(None, description="Fingerprints")
    partial_fingerprints: dict[str, Any] | None = Field(
        None, description="Partial fingerprints"
    )
    properties: dict[str, Any] | None = Field(None, description="Result properties")
    suppressions: list[dict[str, Any]] | None = Field(None, description="Suppressions")
    code_flows: list[dict[str, Any]] | None = Field(None, description="Code flows")


class SemgrepSummary(BaseModel):
    """Semgrep summary for linter result."""

    severity: str | None = Field(None, description="Result severity")
    likelihood: str | None = Field(None, description="Result likelihood")
    confidence: str | None = Field(None, description="Result confidence")
    tags: list[str] | None = Field(None, description="Result tags")
    description: str | None = Field(None, description="Result description")
    explanation: str | None = Field(None, description="Result explanation")
    remediation: str | None = Field(None, description="Result remediation")
    impact: str | None = Field(None, description="Result impact")
    languages: list[str] | None = Field(None, description="Result languages")
    rule_name: str | None = Field(None, description="Rule name")
    rule_uuid: str | None = Field(None, description="Rule UUID")
    cwes: list[str] | None = Field(None, description="CWE identifiers")
    rule_version: str | None = Field(None, description="Rule version")
    references: list[str] | None = Field(None, description="Rule references")


class SecretSummary(BaseModel):
    """Secret summary for linter result."""

    validation: str | None = Field(None, description="Validation status")
    git_log_scanned: bool | None = Field(
        None, description="Whether secret was found in Git logs"
    )
    secret_id: str | None = Field(None, description="Unique identifier for the secret")
    fs_scanned: bool | None = Field(
        None, description="Whether secret was found in filesystem"
    )


class AISastSummary(BaseModel):
    """AI SAST summary for linter result."""

    rule_id: str = Field(..., description="AI SAST rule ID")
    message: str = Field(..., description="Result message")
    severity: str = Field(..., description="Result severity")
    confidence: str = Field(..., description="Result confidence")


class LinterCorrectnessAnalysis(BaseModel):
    """Linter correctness analysis."""

    analysis_type: str = Field(..., description="Type of analysis")
    result: str = Field(..., description="Analysis result")
    confidence: float | None = Field(None, description="Analysis confidence")


class LinterResultMeta(BaseMeta):
    """LinterResult metadata extending BaseMeta."""

    # LinterResult-specific fields only (universal fields inherited from BaseMeta)
    pass


class LinterResultSpec(BaseSpec):
    """LinterResult specification extending BaseSpec.

    Field Mutability Guide:
    ======================

    IMMUTABLE FIELDS (cannot be updated after creation):
    - project_uuid: Project assignment (set at creation)
    - origin: Result origin (set at creation)
    - level: Result level (set at creation)
    - extra_key: Extra key (set at creation)
    - version: Version (set at creation)
    - sarif_result: SARIF result (set at creation)
    - ecosystem: Result ecosystem (set at creation)
    - semgrep: Semgrep summary (set at creation)
    - secret: Secret summary (set at creation)
    - aisast: AI SAST summary (set at creation)
    - fingerprints: Fingerprints (set at creation)
    - fingerprint_count: Fingerprint count (set at creation)
    - distribution_format: Distribution format (set at creation)
    - ref: Git reference (set at creation)
    - storage_location: Storage location (set at creation)
    - suppressed: Suppressed flag (set at creation)
    - linter_correctness_analyses: Correctness analyses (set at creation)

    MUTABLE FIELDS (can be updated via API):
    - None (LinterResult is typically immutable after creation)
    """

    project_uuid: str = Field(
        ..., description="The UUID of the project to which this result is related"
    )  # IMMUTABLE: Set at creation
    origin: LinterResultOrigin = Field(
        ..., description="The origin of the result"
    )  # IMMUTABLE: Set at creation
    level: LinterResultLevel = Field(
        ..., description="The level of the result"
    )  # IMMUTABLE: Set at creation
    extra_key: str = Field(
        ...,
        description="Additional info that may create a unique linter result",
    )  # IMMUTABLE: Set at creation
    version: str | None = Field(
        None, description="Version information"
    )  # IMMUTABLE: Set at creation
    sarif_result: SarifResult | None = Field(
        None, description="SARIF result data"
    )  # IMMUTABLE: Set at creation

    @field_validator("sarif_result", mode="before")
    @classmethod
    def validate_sarif_result(cls, v: Any) -> Any:
        """Handle sarif result validation."""
        if isinstance(v, dict):
            return SarifResult(**v)
        return v

    ecosystem: Ecosystem | None = Field(
        None, description="The result ecosystem"
    )  # IMMUTABLE: Set at creation
    semgrep: SemgrepSummary | None = Field(
        None, description="Semgrep summary"
    )  # IMMUTABLE: Set at creation

    @field_validator("semgrep", mode="before")
    @classmethod
    def validate_semgrep(cls, v: Any) -> Any:
        """Handle semgrep validation."""
        if isinstance(v, dict):
            return SemgrepSummary(**v)
        return v

    secret: SecretSummary | None = Field(
        None, description="Secret summary"
    )  # IMMUTABLE: Set at creation

    @field_validator("secret", mode="before")
    @classmethod
    def validate_secret(cls, v: Any) -> Any:
        """Handle secret validation."""
        if isinstance(v, dict):
            return SecretSummary(**v)
        return v

    aisast: AISastSummary | None = Field(
        None, description="AI SAST summary"
    )  # IMMUTABLE: Set at creation
    fingerprints: list[str] | None = Field(
        None, description="The list and count of found fingerprints"
    )  # IMMUTABLE: Set at creation
    fingerprint_count: int | None = Field(
        None, description="Fingerprint count"
    )  # IMMUTABLE: Set at creation
    distribution_format: DistributionFormatType | None = Field(
        None, description="The distribution format of the package"
    )  # IMMUTABLE: Set at creation
    ref: str | None = Field(
        None, description="The Git reference of the repository version"
    )  # IMMUTABLE: Set at creation
    storage_location: str | None = Field(
        None,
        description="The storage location of the package related to this linter result",
    )  # IMMUTABLE: Set at creation
    suppressed: bool | None = Field(
        None, description="Result was suppressed by semgrep"
    )  # IMMUTABLE: Set at creation
    linter_correctness_analyses: list[LinterCorrectnessAnalysis] | None = Field(
        None, description="An analysis of the linter result"
    )  # IMMUTABLE: Set at creation

    @field_validator("origin", mode="before")
    @classmethod
    def validate_origin(cls, v: Any) -> Any:
        """Handle unknown origin values gracefully."""
        if isinstance(v, str):
            try:
                return LinterResultOrigin(v)
            except ValueError:
                logger.warning(f"Unknown LinterResultOrigin value: {v}. Using as-is.")
                return v
        return v

    @field_validator("level", mode="before")
    @classmethod
    def validate_level(cls, v: Any) -> Any:
        """Handle unknown level values gracefully."""
        if isinstance(v, str):
            try:
                return LinterResultLevel(v)
            except ValueError:
                logger.warning(f"Unknown LinterResultLevel value: {v}. Using as-is.")
                return v
        return v

    @field_validator("ecosystem", mode="before")
    @classmethod
    def validate_ecosystem(cls, v: Any) -> Any:
        """Handle unknown ecosystem values gracefully."""
        if isinstance(v, str):
            try:
                return Ecosystem(v)
            except ValueError:
                logger.warning(f"Unknown Ecosystem value: {v}. Using as-is.")
                return v
        return v

    @field_validator("distribution_format", mode="before")
    @classmethod
    def validate_distribution_format(cls, v: Any) -> Any:
        """Handle unknown distribution format values gracefully."""
        if isinstance(v, str):
            try:
                return DistributionFormatType(v)
            except ValueError:
                logger.warning(
                    f"Unknown DistributionFormatType value: {v}. Using as-is."
                )
                return v
        return v


class LinterResult(BaseResource):
    """LinterResult resource model extending BaseResource.

    **Intermediate Resource (IR) for Debugging:**

    LinterResult contains raw scan output from security scanning tools
    (Semgrep, Gitleaks, etc.) before it's processed into Findings. This
    resource is valuable for debugging the scan → finding pipeline.

    **Key Attributes for Debugging:**

    - `spec.sarif_result`: Full SARIF output with structured locations,
      code snippets, and code flows
    - `spec.semgrep`: Semgrep scan results with rule metadata
    - `spec.origin`: Scan tool origin (SEMGREP, SECRETS_SCANNER, etc.)
    - `spec.ref`: Git reference scanned
    - `spec.version`: Version information at scan time
    - `spec.ecosystem`: Package ecosystem scanned
    - `spec.fingerprints`: Code fingerprints for deduplication
    - `spec.linter_correctness_analyses`: Correctness analysis results

    **Most users should use Finding instead**, but LinterResult is
    essential for troubleshooting finding generation issues.
    """

    # LinterResult-specific fields (universal fields inherited from BaseResource)
    spec: LinterResultSpec = Field(..., description="LinterResult specification")  # type: ignore

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data: Any) -> None:
        # Convert spec to LinterResultSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = LinterResultSpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "project_uuid",
                "origin",
                "level",
                "extra_key",
                "version",
                "sarif_result",
                "ecosystem",
                "semgrep",
                "secret",
                "aisast",
                "fingerprints",
                "fingerprint_count",
                "distribution_format",
                "ref",
                "storage_location",
                "suppressed",
                "linter_correctness_analyses",
            }
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v


def _get_linter_result_ops(client: APIClient) -> BaseResourceOperations[LinterResult]:
    """Get BaseResourceOperations instance for LinterResult."""
    return BaseResourceOperations(client, "linter-results", LinterResult)


def list_linter_results(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    **kwargs: Any,
) -> list[LinterResult]:
    """List linter results with advanced filtering and pagination.

    **Debugging Use Cases:**

    - Query scan results that didn't become findings
    - Analyze scan execution context (Git ref, version, ecosystem)
    - Access full SARIF output for code flow analysis
    - Investigate deduplication logic via fingerprints
    - Trace severity transformations from rule → scan → finding

    **Note**: Most users should query Findings instead. Use LinterResult
    when you need the raw scan output or execution context for debugging.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        list_params: Optional list parameters for filtering, pagination, etc.
        **kwargs: Additional query parameters

    Returns:
        List of LinterResult objects

    """
    ops = _get_linter_result_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)


def get_linter_result(
    client: APIClient, tenant_meta_namespace: str, linter_result_uuid: str
) -> LinterResult:
    """Get specific linter result by UUID.

    **Debugging Use Cases:**

    - Access full SARIF output with code flows and locations
    - View scan execution context (Git ref, version, ecosystem)
    - Inspect code fingerprints and correctness analysis
    - Understand why a scan result did or didn't become a finding

    **Note**: Most users should query Findings instead. Use LinterResult
    when you need the raw scan output for debugging.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        linter_result_uuid: UUID of the linter result

    Returns:
        LinterResult object

    Raises:
        NotFoundError: If linter result doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    ops = _get_linter_result_ops(client)
    return ops.get(tenant_meta_namespace, linter_result_uuid)


def create_linter_result(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateLinterResultPayload,
) -> LinterResult:
    """Create a new linter result with pre-validation and typed errors.

    Raises:
        ValidationError: If payload is invalid
        NotFoundError: If namespace doesn't exist
        PermissionDeniedError: If user lacks permission
        ConflictError: If linter result already exists
        ServerError: If server error occurs

    """
    ops = _get_linter_result_ops(client)
    return ops.create(tenant_meta_namespace, payload)


def update_linter_result(
    client: APIClient,
    tenant_meta_namespace: str,
    linter_result_uuid: str,
    payload: UpdateLinterResultPayload,
    update_mask: str | None = None,
) -> LinterResult | None:
    """Update an existing linter result with partial updates.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        linter_result_uuid: UUID of the linter result to update
        payload: LinterResult update payload
        update_mask: Optional comma-separated list of fields to update
            (e.g., "meta.tags,meta.description"). If provided, only these
            fields will be updated. If omitted, all non-None fields in
            payload will be updated.

    Returns:
        Updated LinterResult object

    Raises:
        ValidationError: If payload is invalid
        NotFoundError: If linter result doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    # Convert update_mask from string to List[str] for base class
    update_mask_list = (
        [field.strip() for field in update_mask.split(",")] if update_mask else None
    )
    ops = _get_linter_result_ops(client)
    return ops.update(
        tenant_meta_namespace, linter_result_uuid, payload, update_mask_list
    )


def delete_linter_result(
    client: APIClient, tenant_meta_namespace: str, linter_result_uuid: str
) -> bool:
    """Delete a linter result by UUID."""
    ops = _get_linter_result_ops(client)
    return ops.delete(tenant_meta_namespace, linter_result_uuid)


# Payload models for create and update operations
class CreateLinterResultPayload(BaseModel):
    """Payload for creating a linter result."""

    meta: LinterResultMetaCreate = Field(
        ..., description="LinterResult metadata for creation"
    )
    spec: LinterResultSpec = Field(..., description="LinterResult specification")


class UpdateLinterResultPayload(BaseModel):
    """Payload for updating a linter result."""

    meta: LinterResultMetaUpdate | None = Field(
        None, description="LinterResult metadata for update"
    )
    spec: LinterResultSpec | None = Field(
        None, description="LinterResult specification for update"
    )


class LinterResultMetaCreate(BaseModel):
    """LinterResult metadata for creation."""

    name: str = Field(..., description="LinterResult name")
    description: str | None = Field(None, description="LinterResult description")


class LinterResultMetaUpdate(BaseModel):
    """LinterResult metadata for update."""

    description: str | None = Field(None, description="LinterResult description")
