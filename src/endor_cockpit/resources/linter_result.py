"""
LinterResult resource module for Endor Labs API.

This module provides CRUD operations for LinterResult resources following the
established patterns from the base class implementation.
"""

import logging
from typing import List, Optional

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
    SOURCE = "DISTRIBUTION_FORMAT_TYPE_SOURCE"
    BINARY = "DISTRIBUTION_FORMAT_TYPE_BINARY"


class Ecosystem(FlexibleEnum):
    """Ecosystem enumeration."""

    UNSPECIFIED = "ECOSYSTEM_UNSPECIFIED"
    GO = "ECOSYSTEM_GO"
    MAVEN = "ECOSYSTEM_MAVEN"
    PYPI = "ECOSYSTEM_PYPI"
    CARGO = "ECOSYSTEM_CARGO"
    NPM = "ECOSYSTEM_NPM"
    GEM = "ECOSYSTEM_GEM"
    NUGET = "ECOSYSTEM_NUGET"
    PACKAGIST = "ECOSYSTEM_PACKAGIST"
    SBOM = "ECOSYSTEM_SBOM"
    RPM = "ECOSYSTEM_RPM"
    DEBIAN = "ECOSYSTEM_DEBIAN"
    GITHUB_ACTION = "ECOSYSTEM_GITHUB_ACTION"


class SarifText(BaseModel):
    """SARIF text object with text and markdown fields."""

    text: Optional[str] = Field(None, description="The actual text content")
    markdown: Optional[str] = Field(
        None, description="Markdown representation of the content"
    )


class SarifResult(BaseModel):
    """SARIF result for linter."""

    rule_id: Optional[str] = Field(None, description="Rule ID")
    message: Optional[SarifText] = Field(None, description="Result message")
    level: Optional[str] = Field(None, description="Result level")
    locations: Optional[List[dict]] = Field(None, description="Result locations")
    fingerprints: Optional[dict] = Field(None, description="Fingerprints")
    partial_fingerprints: Optional[dict] = Field(
        None, description="Partial fingerprints"
    )
    properties: Optional[dict] = Field(None, description="Result properties")
    suppressions: Optional[List[dict]] = Field(None, description="Suppressions")
    code_flows: Optional[List[dict]] = Field(None, description="Code flows")


class SemgrepSummary(BaseModel):
    """Semgrep summary for linter result."""

    severity: Optional[str] = Field(None, description="Result severity")
    likelihood: Optional[str] = Field(None, description="Result likelihood")
    confidence: Optional[str] = Field(None, description="Result confidence")
    tags: Optional[List[str]] = Field(None, description="Result tags")
    description: Optional[str] = Field(None, description="Result description")
    explanation: Optional[str] = Field(None, description="Result explanation")
    remediation: Optional[str] = Field(None, description="Result remediation")
    impact: Optional[str] = Field(None, description="Result impact")
    languages: Optional[List[str]] = Field(None, description="Result languages")
    rule_name: Optional[str] = Field(None, description="Rule name")
    rule_uuid: Optional[str] = Field(None, description="Rule UUID")
    cwes: Optional[List[str]] = Field(None, description="CWE identifiers")
    rule_version: Optional[str] = Field(None, description="Rule version")
    references: Optional[List[str]] = Field(None, description="Rule references")


class SecretSummary(BaseModel):
    """Secret summary for linter result."""

    validation: Optional[str] = Field(None, description="Validation status")
    git_log_scanned: Optional[bool] = Field(
        None, description="Whether secret was found in Git logs"
    )
    secret_id: Optional[str] = Field(
        None, description="Unique identifier for the secret"
    )
    fs_scanned: Optional[bool] = Field(
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
    confidence: Optional[float] = Field(None, description="Analysis confidence")


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
    version: Optional[str] = Field(
        None, description="Version information"
    )  # IMMUTABLE: Set at creation
    sarif_result: Optional[SarifResult] = Field(
        None, description="SARIF result data"
    )  # IMMUTABLE: Set at creation

    @field_validator("sarif_result", mode="before")
    @classmethod
    def validate_sarif_result(cls, v):
        """Handle sarif result validation."""
        if isinstance(v, dict):
            return SarifResult(**v)
        return v
    ecosystem: Optional[Ecosystem] = Field(
        None, description="The result ecosystem"
    )  # IMMUTABLE: Set at creation
    semgrep: Optional[SemgrepSummary] = Field(
        None, description="Semgrep summary"
    )  # IMMUTABLE: Set at creation

    @field_validator("semgrep", mode="before")
    @classmethod
    def validate_semgrep(cls, v):
        """Handle semgrep validation."""
        if isinstance(v, dict):
            return SemgrepSummary(**v)
        return v
    secret: Optional[SecretSummary] = Field(
        None, description="Secret summary"
    )  # IMMUTABLE: Set at creation

    @field_validator("secret", mode="before")
    @classmethod
    def validate_secret(cls, v):
        """Handle secret validation."""
        if isinstance(v, dict):
            return SecretSummary(**v)
        return v
    aisast: Optional[AISastSummary] = Field(
        None, description="AI SAST summary"
    )  # IMMUTABLE: Set at creation
    fingerprints: Optional[List[str]] = Field(
        None, description="The list and count of found fingerprints"
    )  # IMMUTABLE: Set at creation
    fingerprint_count: Optional[int] = Field(
        None, description="Fingerprint count"
    )  # IMMUTABLE: Set at creation
    distribution_format: Optional[DistributionFormatType] = Field(
        None, description="The distribution format of the package"
    )  # IMMUTABLE: Set at creation
    ref: Optional[str] = Field(
        None, description="The Git reference of the repository version"
    )  # IMMUTABLE: Set at creation
    storage_location: Optional[str] = Field(
        None,
        description="The storage location of the package related to this linter result",
    )  # IMMUTABLE: Set at creation
    suppressed: Optional[bool] = Field(
        None, description="Result was suppressed by semgrep"
    )  # IMMUTABLE: Set at creation
    linter_correctness_analyses: Optional[List[LinterCorrectnessAnalysis]] = Field(
        None, description="An analysis of the linter result"
    )  # IMMUTABLE: Set at creation

    @field_validator("origin", mode="before")
    @classmethod
    def validate_origin(cls, v):
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
    def validate_level(cls, v):
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
    def validate_ecosystem(cls, v):
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
    def validate_distribution_format(cls, v):
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
    """LinterResult resource model extending BaseResource."""

    # LinterResult-specific fields (universal fields inherited from BaseResource)
    spec: LinterResultSpec = Field(..., description="LinterResult specification")  # type: ignore

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data):
        # Convert spec to LinterResultSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = LinterResultSpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
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


def _get_linter_result_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for LinterResult."""
    return BaseResourceOperations(client, "linter-results", LinterResult)


def list_linter_results(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
    **kwargs,
) -> List[LinterResult]:
    """List linter results with advanced filtering and pagination."""
    ops = _get_linter_result_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)  # type: ignore


def get_linter_result(
    client: APIClient, tenant_meta_namespace: str, linter_result_uuid: str
) -> Optional[LinterResult]:
    """Get specific linter result by UUID."""
    ops = _get_linter_result_ops(client)
    return ops.get(tenant_meta_namespace, linter_result_uuid)  # type: ignore


def create_linter_result(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: "CreateLinterResultPayload",
) -> Optional[LinterResult]:
    """Create a new linter result."""
    ops = _get_linter_result_ops(client)
    return ops.create(tenant_meta_namespace, payload)  # type: ignore


def update_linter_result(
    client: APIClient,
    tenant_meta_namespace: str,
    linter_result_uuid: str,
    payload: "UpdateLinterResultPayload",
    update_mask: Optional[List[str]] = None,
) -> Optional[LinterResult]:
    """Update an existing linter result with partial updates."""
    ops = _get_linter_result_ops(client)
    return ops.update(tenant_meta_namespace, linter_result_uuid, payload, update_mask)  # type: ignore


def delete_linter_result(
    client: APIClient, tenant_meta_namespace: str, linter_result_uuid: str
) -> bool:
    """Delete a linter result by UUID."""
    ops = _get_linter_result_ops(client)
    return ops.delete(tenant_meta_namespace, linter_result_uuid)  # type: ignore


# Payload models for create and update operations
class CreateLinterResultPayload(BaseModel):
    """Payload for creating a linter result."""

    meta: "LinterResultMetaCreate" = Field(
        ..., description="LinterResult metadata for creation"
    )
    spec: LinterResultSpec = Field(..., description="LinterResult specification")


class UpdateLinterResultPayload(BaseModel):
    """Payload for updating a linter result."""

    meta: Optional["LinterResultMetaUpdate"] = Field(
        None, description="LinterResult metadata for update"
    )
    spec: Optional[LinterResultSpec] = Field(
        None, description="LinterResult specification for update"
    )


class LinterResultMetaCreate(BaseModel):
    """LinterResult metadata for creation."""

    name: str = Field(..., description="LinterResult name")
    description: Optional[str] = Field(None, description="LinterResult description")


class LinterResultMetaUpdate(BaseModel):
    """LinterResult metadata for update."""

    description: Optional[str] = Field(None, description="LinterResult description")
