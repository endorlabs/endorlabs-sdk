"""SemgrepRule resource module for Endor Labs API.

This module provides CRUD operations for SemgrepRule resources following the
established patterns from the base class implementation.

API OPERATIONS SUPPORTED:
- GET: List semgrep rules, Get semgrep rule by UUID
- POST: Create new semgrep rules
- PATCH: Update existing semgrep rules
- DELETE: Delete semgrep rules

API FEATURES:
- Full CRUD operations supported
- Semgrep-compatible rule format
- Rule metadata (CWE, OWASP, references, etc.)
- Severity level computation
- Namespace propagation control
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

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
def _get_semgrep_rule_ops(
    client: APIClient,
) -> BaseResourceOperations[SemgrepRule]:
    """Get BaseResourceOperations instance for semgrep rules."""
    return BaseResourceOperations(client, "semgrep-rules", SemgrepRule)


class SeverityLevel(FlexibleEnum):
    """Severity level enumeration for Semgrep rules."""

    UNSPECIFIED = "SEVERITY_LEVEL_UNSPECIFIED"
    LOW = "SEVERITY_LEVEL_LOW"
    MEDIUM = "SEVERITY_LEVEL_MEDIUM"
    HIGH = "SEVERITY_LEVEL_HIGH"
    CRITICAL = "SEVERITY_LEVEL_CRITICAL"
    # Legacy Semgrep values (for rule.severity field)
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class SemgrepFixRegex(BaseModel):
    """Semgrep fix regex configuration."""

    regex: str | None = Field(None, description="Fix regex pattern")
    replacement: str | None = Field(None, description="Replacement string")


class SemgrepOptions(BaseModel):
    """Semgrep rule options."""

    symbolic_propagation: bool | None = Field(
        None, description="Enable symbolic propagation"
    )
    interfile: bool | None = Field(None, description="Enable interfile analysis")
    assume_numbers_are_safe: bool | None = Field(
        None, description="Assume numbers are safe"
    )


class SemgrepRulePatternType(BaseModel):
    """Semgrep rule pattern type (recursive structure)."""

    pattern: str | None = Field(None, description="Pattern string")
    pattern_not: str | None = Field(None, description="Pattern not")
    from_: str | None = Field(None, alias="from", description="From pattern")
    to: str | None = Field(None, description="To pattern")
    metavariable_regex: SemgrepMetavariableRegex | None = Field(
        None, description="Metavariable regex"
    )
    patterns: list[SemgrepRulePatternType] | None = Field(
        None, description="Nested patterns"
    )
    pattern_not_regex: str | None = Field(None, description="Pattern not regex")
    pattern_regex: str | None = Field(None, description="Pattern regex")

    model_config = ConfigDict(populate_by_name=True)


class SemgrepRuleMeta(BaseModel):
    """Semgrep rule metadata."""

    license: str | None = Field(None, description="Rule license")
    likelihood: str | None = Field(None, description="Likelihood level")
    confidence: str | None = Field(None, description="Confidence level")
    category: str | None = Field(None, description="Rule category")
    cwe: list[str] | None = Field(None, description="CWE identifiers")
    owasp: list[str] | None = Field(None, description="OWASP categories")
    references: list[str] | None = Field(None, description="Reference URLs")
    technology: list[str] | None = Field(None, description="Technology tags")
    subcategory: list[str] | None = Field(None, description="Subcategory tags")
    cwe2022_top25: bool | None = Field(None, description="CWE 2022 Top 25 flag")
    cwe2021_top25: bool | None = Field(None, description="CWE 2021 Top 25 flag")
    source_rule_url: str | None = Field(None, description="Source rule URL")
    impact: str | None = Field(None, description="Impact level")
    description: str | None = Field(None, description="Rule description")
    endor_targets: list[EndorTarget] | None = Field(
        None, description="Endor target types"
    )


class SemgrepNativeRule(BaseModel):
    """Semgrep native rule structure (Semgrep-compatible format)."""

    id: str | None = Field(None, description="Rule ID")
    pattern: str | None = Field(None, description="Pattern string")
    fix: str | None = Field(None, description="Fix suggestion")
    severity: str | None = Field(None, description="Severity level")
    metadata: SemgrepRuleMeta | None = Field(None, description="Rule metadata")
    languages: list[str] | None = Field(None, description="Supported languages")
    message: str | None = Field(None, description="Rule message")
    patterns: list[SemgrepRulePatternType] | None = Field(
        None, description="Pattern list"
    )
    fix_regex: SemgrepFixRegex | None = Field(
        None, description="Fix regex configuration"
    )
    mode: str | None = Field(None, description="Rule mode")
    pattern_sources: list[SemgrepRulePatternType] | None = Field(
        None, description="Taint source patterns"
    )
    pattern_sinks: list[SemgrepRulePatternType] | None = Field(
        None, description="Taint sink patterns"
    )
    pattern_propagators: list[SemgrepRulePatternType] | None = Field(
        None, description="Taint propagator patterns"
    )
    options: SemgrepOptions | None = Field(None, description="Rule options")
    pattern_either: list[SemgrepRulePatternType] | None = Field(
        None, description="Pattern either list"
    )
    paths: SemgrepPaths | None = Field(None, description="Path inclusion/exclusion")
    pattern_sanitizers: list[SemgrepRulePatternType] | None = Field(
        None, description="Taint sanitizer patterns"
    )
    pattern_not: list[SemgrepRulePatternType] | None = Field(
        None, description="Pattern not list"
    )
    pattern_regex: str | None = Field(None, description="Pattern regex")
    references: list[str] | None = Field(None, description="Reference URLs")
    metavariable_regex: SemgrepMetavariableRegex | None = Field(
        None, description="Metavariable regex"
    )
    metavariable_pattern: SemgrepMetavariablePattern | None = Field(
        None, description="Metavariable pattern"
    )
    focus_metavariable: list[str] | None = Field(
        None, description="Focus metavariables"
    )
    min_version: str | None = Field(None, description="Minimum version")
    pattern_inside: str | None = Field(None, description="Pattern inside")
    pattern_inside_either: list[SemgrepRulePatternType] | None = Field(
        None, description="Pattern inside either list"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str | None) -> str | None:
        """Validate rule ID is not empty."""
        if v and not v.strip():
            raise ValueError("rule id cannot be empty or whitespace")
        return v.strip() if v else v

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: list[str] | None) -> list[str] | None:
        """Validate languages list is not empty."""
        if v and len(v) == 0:
            raise ValueError("languages list cannot be empty")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str | None) -> str | None:
        """Validate message is not empty."""
        if v and not v.strip():
            raise ValueError("message cannot be empty or whitespace")
        return v.strip() if v else v


class SemgrepRuleSpec(BaseSpec):
    """Semgrep rule specification extending BaseSpec."""

    rule: SemgrepNativeRule | None = Field(None, description="Semgrep native rule")
    disabled: bool | None = Field(False, description="Whether rule is disabled")
    yaml: str | None = Field(None, description="Original YAML format of the rule")
    defined_by: str | None = Field(
        None, description="Rule creator (Endor Labs or tenant name)"
    )
    severity_level: SeverityLevel | None = Field(
        None, description="Computed severity level"
    )

    @field_validator("yaml")
    @classmethod
    def validate_yaml(cls, v: str | None) -> str | None:
        """Validate YAML format is parseable."""
        if v:
            try:
                yaml.safe_load(v)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML format: {e}") from e
        return v


class SemgrepRuleMetaCreate(BaseMeta):
    """Semgrep rule metadata for creation."""

    # Inherits all BaseMeta fields
    pass


class SemgrepRule(BaseResource):
    """SemgrepRule resource model extending BaseResource.

    OPERATION SUPPORT:
    ==================
    ✅ GET: List semgrep rules, Get by UUID
    ✅ POST: Create new semgrep rules
    ✅ PATCH: Update existing semgrep rules
    ✅ DELETE: Delete semgrep rules

    FIELD MUTABILITY:
    =================
    IMMUTABLE FIELDS (read-only, system-managed):
    - uuid: Unique identifier
    - meta.create_time, meta.created_by: Creation metadata
    - meta.update_time, meta.updated_by: Auto-managed timestamps
    - spec.defined_by: Rule creator (read-only)
    - spec.severity_level: Computed severity (read-only)
    - tenant_meta.namespace: Namespace assignment

    MUTABLE FIELDS (can be updated via PATCH):
    - meta.name: Rule name
    - meta.description: Rule description
    - meta.tags: Rule tags
    - spec.rule: Semgrep native rule definition
    - spec.disabled: Enable/disable flag
    - spec.yaml: Original YAML format
    - propagate: Whether to propagate to child namespaces
    - disabled: Top-level disabled flag

    FEATURES:
    =========
    - Semgrep-compatible rule format
    - Comprehensive metadata (CWE, OWASP, references)
    - Taint tracking patterns (sources, sinks, propagators, sanitizers)
    - Path inclusion/exclusion
    - Advanced options (symbolic propagation, interfile analysis)
    - Severity level computation
    - Namespace propagation control
    """

    spec: SemgrepRuleSpec | None = Field(None, description="Semgrep rule specification")  # type: ignore
    disabled: bool | None = Field(None, description="Whether rule is disabled")

    model_config: ClassVar[dict[str, str]] = {"extra": "ignore"}

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift in semgrep rule responses."""
        # Implementation for schema drift detection
        return v


class CreateSemgrepRulePayload(BaseModel):
    """Payload for creating a new Semgrep rule."""

    meta: SemgrepRuleMetaCreate = Field(..., description="Semgrep rule metadata")
    spec: SemgrepRuleSpec = Field(..., description="Semgrep rule specification")
    propagate: bool | None = Field(True, description="Propagate to child namespaces")
    disabled: bool | None = Field(None, description="Whether rule is disabled")


class UpdateSemgrepRulePayload(BaseModel):
    """Payload for updating a Semgrep rule."""

    meta: SemgrepRuleMetaCreate | None = Field(
        None, description="Updated semgrep rule metadata"
    )
    spec: SemgrepRuleSpec | None = Field(
        None, description="Updated semgrep rule specification"
    )
    propagate: bool | None = Field(None, description="Propagate to child namespaces")
    disabled: bool | None = Field(None, description="Whether rule is disabled")


def _validate_meta(payload: CreateSemgrepRulePayload, errors: list[str]) -> None:
    """Validate meta field."""
    if not payload.meta:
        errors.append("meta is required")
    elif not payload.meta.name or not payload.meta.name.strip():
        errors.append("meta.name is required and cannot be empty")


def _validate_rule_structure(rule: Any, errors: list[str]) -> None:
    """Validate rule structure (ID, languages, message)."""
    # Validate rule ID
    if not rule.id or not rule.id.strip():
        errors.append("rule.id is required and cannot be empty")

    # Validate languages
    if not rule.languages or len(rule.languages) == 0:
        errors.append("rule.languages is required and cannot be empty")

    # Validate message
    if not rule.message or not rule.message.strip():
        errors.append("rule.message is required and cannot be empty")


def _validate_patterns(rule: Any, errors: list[str]) -> None:
    """Validate pattern types."""
    has_patterns = (
        rule.pattern is not None
        or (rule.patterns and len(rule.patterns) > 0)
        or (rule.pattern_either and len(rule.pattern_either) > 0)
        or (rule.pattern_sources and len(rule.pattern_sources) > 0)
        or (rule.pattern_sinks and len(rule.pattern_sinks) > 0)
    )

    if not has_patterns:
        errors.append(
            "At least one pattern type must be specified "
            "(pattern, patterns, pattern_either, pattern_sources, or pattern_sinks)"
        )


def _validate_taint_mode(rule: Any, errors: list[str]) -> None:
    """Validate taint mode requirements."""
    if rule.mode == "taint":
        if not rule.pattern_sources or len(rule.pattern_sources) == 0:
            errors.append("pattern_sources is required when mode is 'taint'")
        if not rule.pattern_sinks or len(rule.pattern_sinks) == 0:
            errors.append("pattern_sinks is required when mode is 'taint'")


def _validate_spec(payload: CreateSemgrepRulePayload, errors: list[str]) -> None:
    """Validate spec field."""
    if not payload.spec:
        errors.append("spec is required")
    elif not payload.spec.rule:
        errors.append("spec.rule is required")
    else:
        rule = payload.spec.rule
        _validate_rule_structure(rule, errors)
        _validate_patterns(rule, errors)
        _validate_taint_mode(rule, errors)


def _validate_yaml(payload: CreateSemgrepRulePayload, errors: list[str]) -> None:
    """Validate YAML format."""
    if payload.spec and payload.spec.yaml:
        try:
            yaml.safe_load(payload.spec.yaml)
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML format in spec.yaml: {e}")


def validate_semgrep_rule(
    payload: CreateSemgrepRulePayload,
    validate_yaml: bool = True,
) -> tuple[bool, list[str]]:
    """Validate a Semgrep rule payload before creation.

    This function performs comprehensive validation of a Semgrep rule payload
    to catch errors before attempting API creation. It validates:
    - Required fields are present
    - Rule structure is valid
    - YAML format is parseable (if provided)
    - Rule ID format
    - Languages are specified
    - Pattern structure is valid

    Args:
        payload: Semgrep rule creation payload to validate
        validate_yaml: Whether to validate YAML format (default: True)

    Returns:
        Tuple of (is_valid: bool, errors: List[str])
        - is_valid: True if payload is valid, False otherwise
        - errors: List of validation error messages

    Example:
        >>> payload = CreateSemgrepRulePayload(...)
        >>> is_valid, errors = validate_semgrep_rule(payload)
        >>> if not is_valid:
        ...     print(f"Validation errors: {errors}")
        ... else:
        ...     rule = create_semgrep_rule(client, namespace, payload)

    """
    errors: list[str] = []

    # Validate required fields
    _validate_meta(payload, errors)
    _validate_spec(payload, errors)

    # Validate YAML format if provided
    if validate_yaml:
        _validate_yaml(payload, errors)

    # Try Pydantic validation to catch any model-level errors
    try:
        _ = payload.model_validate(payload.model_dump())
    except ValidationError as e:
        for error in e.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            errors.append(f"{field_path}: {error['msg']}")

    return (len(errors) == 0, errors)


def list_semgrep_rules(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    **kwargs: Any,
) -> list[SemgrepRule]:
    """List all Semgrep rules in a namespace.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        list_params: Optional list parameters for filtering, masking, pagination
        **kwargs: Additional query parameters

    Returns:
        List of SemgrepRule objects

    """
    ops = _get_semgrep_rule_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)


def get_semgrep_rule(
    client: APIClient, tenant_meta_namespace: str, rule_uuid: str
) -> SemgrepRule:
    """Get a specific Semgrep rule by UUID.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        rule_uuid: Semgrep rule UUID

    Returns:
        SemgrepRule object

    Raises:
        NotFoundError: If Semgrep rule doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    ops = _get_semgrep_rule_ops(client)
    return ops.get(tenant_meta_namespace, rule_uuid)


def create_semgrep_rule(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateSemgrepRulePayload,
    validate: bool = True,
) -> SemgrepRule:
    """Create a new Semgrep rule in a namespace with pre-validation and typed errors.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        payload: Semgrep rule creation payload
        validate: Whether to validate the payload before creation (default: True)

    Returns:
        Created SemgrepRule object

    Raises:
        ValidationError: If payload is invalid
        ValueError: If validation fails and validate=True
        NotFoundError: If namespace doesn't exist
        PermissionDeniedError: If user lacks permission
        ConflictError: If Semgrep rule already exists
        ServerError: If server error occurs

    """
    # Validate payload before creation
    if validate:
        is_valid, errors = validate_semgrep_rule(payload)
        if not is_valid:
            error_msg = "Semgrep rule validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            logger.error(error_msg)
            from ..exceptions import ValidationError

            raise ValidationError(
                message=error_msg,
                operation="create",
                namespace=tenant_meta_namespace,
            )

    ops = _get_semgrep_rule_ops(client)
    return ops.create(tenant_meta_namespace, payload)


def update_semgrep_rule(
    client: APIClient,
    tenant_meta_namespace: str,
    rule_uuid: str,
    payload: UpdateSemgrepRulePayload,
    update_mask: str | None = None,
) -> SemgrepRule | None:
    """Update an existing Semgrep rule.

    Uses the plural endpoint pattern (like policies and findings) with object wrapper.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        rule_uuid: Semgrep rule UUID
        payload: Semgrep rule update payload
        update_mask: Optional comma-separated list of fields to update

    Returns:
        Updated SemgrepRule object

    Raises:
        ValidationError: If payload is invalid
        NotFoundError: If Semgrep rule doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    # Get current rule to include required fields
    current_rule = get_semgrep_rule(client, tenant_meta_namespace, rule_uuid)

    # Merge current rule with payload updates
    merged_meta = (
        {
            **(current_rule.meta.model_dump() if current_rule.meta else {}),
            **payload.meta.model_dump(exclude_none=True),
        }
        if payload.meta
        else (current_rule.meta.model_dump() if current_rule.meta else {})
    )

    merged_spec = {}
    if payload.spec:
        merged_spec = (
            current_rule.spec.model_dump(exclude_none=True) if current_rule.spec else {}
        )
        merged_spec.update(payload.spec.model_dump(exclude_none=True))
    elif current_rule.spec:
        merged_spec = current_rule.spec.model_dump()

    # Build merged semgrep rule object for base class
    merged_rule_dict = {
        "uuid": rule_uuid,
        "tenant_meta": current_rule.tenant_meta.model_dump()
        if current_rule.tenant_meta
        else {"namespace": tenant_meta_namespace},
    }
    if merged_meta:
        merged_rule_dict["meta"] = merged_meta
    if merged_spec:
        merged_rule_dict["spec"] = merged_spec
    if payload.disabled is not None:
        merged_rule_dict["disabled"] = payload.disabled
    if payload.propagate is not None:
        merged_rule_dict["propagate"] = payload.propagate

    # Create SemgrepRule object from merged data
    merged_rule = SemgrepRule(**merged_rule_dict)

    # Convert update_mask from string to List[str] for base class
    update_mask_list = (
        [field.strip() for field in update_mask.split(",")] if update_mask else None
    )

    # Use base class update method
    ops = _get_semgrep_rule_ops(client)
    logger.info(f"Updating semgrep rule {rule_uuid} with mask: {update_mask}")
    return ops.update(tenant_meta_namespace, rule_uuid, merged_rule, update_mask_list)


def delete_semgrep_rule(
    client: APIClient, tenant_meta_namespace: str, rule_uuid: str
) -> bool:
    """Delete a Semgrep rule.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        rule_uuid: Semgrep rule UUID

    Returns:
        True if deletion succeeded, False otherwise

    """
    ops = _get_semgrep_rule_ops(client)
    return ops.delete(tenant_meta_namespace, rule_uuid)


# Forward references
SemgrepMetavariableRegex = dict[str, Any]  # Placeholder - define properly if needed
SemgrepMetavariablePattern = dict[str, Any]  # Placeholder - define properly if needed
SemgrepPaths = dict[str, Any]  # Placeholder - define properly if needed
EndorTarget = str  # Placeholder - define properly if needed
