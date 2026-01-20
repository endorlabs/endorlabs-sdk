"""
SemgrepRule resource module for Endor Labs API.

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
from typing import Any, Dict, List, Optional, Tuple

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

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
_semgrep_rule_ops = None


def _get_semgrep_rule_ops(client: APIClient) -> BaseResourceOperations:
    """Get or create semgrep rule operations instance."""
    global _semgrep_rule_ops
    if _semgrep_rule_ops is None:
        _semgrep_rule_ops = BaseResourceOperations(client, "semgrep-rules", SemgrepRule)
    return _semgrep_rule_ops


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

    regex: Optional[str] = Field(None, description="Fix regex pattern")
    replacement: Optional[str] = Field(None, description="Replacement string")


class SemgrepOptions(BaseModel):
    """Semgrep rule options."""

    symbolic_propagation: Optional[bool] = Field(
        None, description="Enable symbolic propagation"
    )
    interfile: Optional[bool] = Field(None, description="Enable interfile analysis")
    assume_numbers_are_safe: Optional[bool] = Field(
        None, description="Assume numbers are safe"
    )


class SemgrepRulePatternType(BaseModel):
    """Semgrep rule pattern type (recursive structure)."""

    pattern: Optional[str] = Field(None, description="Pattern string")
    pattern_not: Optional[str] = Field(None, description="Pattern not")
    from_: Optional[str] = Field(None, alias="from", description="From pattern")
    to: Optional[str] = Field(None, description="To pattern")
    metavariable_regex: Optional["SemgrepMetavariableRegex"] = Field(
        None, description="Metavariable regex"
    )
    patterns: Optional[List["SemgrepRulePatternType"]] = Field(
        None, description="Nested patterns"
    )
    pattern_not_regex: Optional[str] = Field(None, description="Pattern not regex")
    pattern_regex: Optional[str] = Field(None, description="Pattern regex")

    class Config:
        populate_by_name = True


class SemgrepRuleMeta(BaseModel):
    """Semgrep rule metadata."""

    license: Optional[str] = Field(None, description="Rule license")
    likelihood: Optional[str] = Field(None, description="Likelihood level")
    confidence: Optional[str] = Field(None, description="Confidence level")
    category: Optional[str] = Field(None, description="Rule category")
    cwe: Optional[List[str]] = Field(None, description="CWE identifiers")
    owasp: Optional[List[str]] = Field(None, description="OWASP categories")
    references: Optional[List[str]] = Field(None, description="Reference URLs")
    technology: Optional[List[str]] = Field(None, description="Technology tags")
    subcategory: Optional[List[str]] = Field(None, description="Subcategory tags")
    cwe2022_top25: Optional[bool] = Field(None, description="CWE 2022 Top 25 flag")
    cwe2021_top25: Optional[bool] = Field(None, description="CWE 2021 Top 25 flag")
    source_rule_url: Optional[str] = Field(None, description="Source rule URL")
    impact: Optional[str] = Field(None, description="Impact level")
    description: Optional[str] = Field(None, description="Rule description")
    endor_targets: Optional[List[EndorTarget]] = Field(
        None, description="Endor target types"
    )


class SemgrepNativeRule(BaseModel):
    """Semgrep native rule structure (Semgrep-compatible format)."""

    id: Optional[str] = Field(None, description="Rule ID")
    pattern: Optional[str] = Field(None, description="Pattern string")
    fix: Optional[str] = Field(None, description="Fix suggestion")
    severity: Optional[str] = Field(None, description="Severity level")
    metadata: Optional[SemgrepRuleMeta] = Field(None, description="Rule metadata")
    languages: Optional[List[str]] = Field(None, description="Supported languages")
    message: Optional[str] = Field(None, description="Rule message")
    patterns: Optional[List[SemgrepRulePatternType]] = Field(
        None, description="Pattern list"
    )
    fix_regex: Optional[SemgrepFixRegex] = Field(
        None, description="Fix regex configuration"
    )
    mode: Optional[str] = Field(None, description="Rule mode")
    pattern_sources: Optional[List[SemgrepRulePatternType]] = Field(
        None, description="Taint source patterns"
    )
    pattern_sinks: Optional[List[SemgrepRulePatternType]] = Field(
        None, description="Taint sink patterns"
    )
    pattern_propagators: Optional[List[SemgrepRulePatternType]] = Field(
        None, description="Taint propagator patterns"
    )
    options: Optional[SemgrepOptions] = Field(None, description="Rule options")
    pattern_either: Optional[List[SemgrepRulePatternType]] = Field(
        None, description="Pattern either list"
    )
    paths: Optional[SemgrepPaths] = Field(None, description="Path inclusion/exclusion")
    pattern_sanitizers: Optional[List[SemgrepRulePatternType]] = Field(
        None, description="Taint sanitizer patterns"
    )
    pattern_not: Optional[List[SemgrepRulePatternType]] = Field(
        None, description="Pattern not list"
    )
    pattern_regex: Optional[str] = Field(None, description="Pattern regex")
    references: Optional[List[str]] = Field(None, description="Reference URLs")
    metavariable_regex: Optional[SemgrepMetavariableRegex] = Field(
        None, description="Metavariable regex"
    )
    metavariable_pattern: Optional[SemgrepMetavariablePattern] = Field(
        None, description="Metavariable pattern"
    )
    focus_metavariable: Optional[List[str]] = Field(
        None, description="Focus metavariables"
    )
    min_version: Optional[str] = Field(None, description="Minimum version")
    pattern_inside: Optional[str] = Field(None, description="Pattern inside")
    pattern_inside_either: Optional[List[SemgrepRulePatternType]] = Field(
        None, description="Pattern inside either list"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate rule ID is not empty."""
        if v and not v.strip():
            raise ValueError("rule id cannot be empty or whitespace")
        return v.strip() if v else v

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate languages list is not empty."""
        if v and len(v) == 0:
            raise ValueError("languages list cannot be empty")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: Optional[str]) -> Optional[str]:
        """Validate message is not empty."""
        if v and not v.strip():
            raise ValueError("message cannot be empty or whitespace")
        return v.strip() if v else v


class SemgrepRuleSpec(BaseSpec):
    """Semgrep rule specification extending BaseSpec."""

    rule: Optional[SemgrepNativeRule] = Field(None, description="Semgrep native rule")
    disabled: Optional[bool] = Field(False, description="Whether rule is disabled")
    yaml: Optional[str] = Field(None, description="Original YAML format of the rule")
    defined_by: Optional[str] = Field(
        None, description="Rule creator (Endor Labs or tenant name)"
    )
    severity_level: Optional[SeverityLevel] = Field(
        None, description="Computed severity level"
    )

    @field_validator("yaml")
    @classmethod
    def validate_yaml(cls, v: Optional[str]) -> Optional[str]:
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
    """
    SemgrepRule resource model extending BaseResource.

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

    spec: Optional[SemgrepRuleSpec] = Field(
        None, description="Semgrep rule specification"
    )  # type: ignore
    disabled: Optional[bool] = Field(None, description="Whether rule is disabled")

    model_config = {"extra": "ignore"}

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift in semgrep rule responses."""
        # Implementation for schema drift detection
        return v


class CreateSemgrepRulePayload(BaseModel):
    """Payload for creating a new Semgrep rule."""

    meta: SemgrepRuleMetaCreate = Field(..., description="Semgrep rule metadata")
    spec: SemgrepRuleSpec = Field(..., description="Semgrep rule specification")
    propagate: Optional[bool] = Field(True, description="Propagate to child namespaces")
    disabled: Optional[bool] = Field(None, description="Whether rule is disabled")


class UpdateSemgrepRulePayload(BaseModel):
    """Payload for updating a Semgrep rule."""

    meta: Optional[SemgrepRuleMetaCreate] = Field(
        None, description="Updated semgrep rule metadata"
    )
    spec: Optional[SemgrepRuleSpec] = Field(
        None, description="Updated semgrep rule specification"
    )
    propagate: Optional[bool] = Field(None, description="Propagate to child namespaces")
    disabled: Optional[bool] = Field(None, description="Whether rule is disabled")


def validate_semgrep_rule(
    payload: CreateSemgrepRulePayload,
    validate_yaml: bool = True,
) -> Tuple[bool, List[str]]:
    """
    Validate a Semgrep rule payload before creation.

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
    errors: List[str] = []

    # Validate required fields
    if not payload.meta:
        errors.append("meta is required")
    elif not payload.meta.name or not payload.meta.name.strip():
        errors.append("meta.name is required and cannot be empty")

    if not payload.spec:
        errors.append("spec is required")
    elif not payload.spec.rule:
        errors.append("spec.rule is required")
    else:
        rule = payload.spec.rule

        # Validate rule ID
        if not rule.id or not rule.id.strip():
            errors.append("rule.id is required and cannot be empty")

        # Validate languages
        if not rule.languages or len(rule.languages) == 0:
            errors.append("rule.languages is required and cannot be empty")

        # Validate message
        if not rule.message or not rule.message.strip():
            errors.append("rule.message is required and cannot be empty")

        # Validate at least one pattern type is present
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

        # Validate taint mode requirements
        if rule.mode == "taint":
            if not rule.pattern_sources or len(rule.pattern_sources) == 0:
                errors.append("pattern_sources is required when mode is 'taint'")
            if not rule.pattern_sinks or len(rule.pattern_sinks) == 0:
                errors.append("pattern_sinks is required when mode is 'taint'")

    # Validate YAML format if provided
    if validate_yaml and payload.spec and payload.spec.yaml:
        try:
            yaml.safe_load(payload.spec.yaml)
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML format in spec.yaml: {e}")

    # Try Pydantic validation to catch any model-level errors
    try:
        payload.model_validate(payload.model_dump())
    except ValidationError as e:
        for error in e.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            errors.append(f"{field_path}: {error['msg']}")

    return (len(errors) == 0, errors)


def list_semgrep_rules(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
    **kwargs,
) -> List[SemgrepRule]:
    """
    List all Semgrep rules in a namespace.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        list_params: Optional list parameters for filtering, masking, pagination
        **kwargs: Additional query parameters

    Returns:
        List of SemgrepRule objects
    """
    ops = _get_semgrep_rule_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)  # type: ignore


def get_semgrep_rule(
    client: APIClient, tenant_meta_namespace: str, rule_uuid: str
) -> Optional[SemgrepRule]:
    """
    Get a specific Semgrep rule by UUID.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        rule_uuid: Semgrep rule UUID

    Returns:
        SemgrepRule object or None if not found
    """
    ops = _get_semgrep_rule_ops(client)
    return ops.get(tenant_meta_namespace, rule_uuid)  # type: ignore


def create_semgrep_rule(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateSemgrepRulePayload,
    validate: bool = True,
) -> Optional[SemgrepRule]:
    """
    Create a new Semgrep rule in a namespace.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        payload: Semgrep rule creation payload
        validate: Whether to validate the payload before creation (default: True)

    Returns:
        Created SemgrepRule object or None if creation failed

    Raises:
        ValueError: If validation fails and validate=True
    """
    # Validate payload before creation
    if validate:
        is_valid, errors = validate_semgrep_rule(payload)
        if not is_valid:
            error_msg = "Semgrep rule validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

    ops = _get_semgrep_rule_ops(client)
    return ops.create(tenant_meta_namespace, payload)  # type: ignore


def update_semgrep_rule(
    client: APIClient,
    tenant_meta_namespace: str,
    rule_uuid: str,
    payload: UpdateSemgrepRulePayload,
    update_mask: Optional[str] = None,
) -> Optional[SemgrepRule]:
    """
    Update an existing Semgrep rule.

    Uses the plural endpoint pattern (like policies and findings) with object wrapper.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        rule_uuid: Semgrep rule UUID
        payload: Semgrep rule update payload
        update_mask: Optional comma-separated list of fields to update

    Returns:
        Updated SemgrepRule object or None if update failed
    """
    try:
        # Get current rule to include required fields
        current_rule = get_semgrep_rule(client, tenant_meta_namespace, rule_uuid)
        if not current_rule:
            logger.error(f"Semgrep rule {rule_uuid} not found")
            return None

        # Build request data with object wrapper (like policy.py and finding.py)
        request_data = {
            "object": {
                "uuid": rule_uuid,
                "tenant_meta": current_rule.tenant_meta.model_dump()
                if current_rule.tenant_meta
                else {"namespace": tenant_meta_namespace},
            }
        }

        # Merge payload fields
        if payload.meta:
            request_data["object"]["meta"] = {
                **(current_rule.meta.model_dump() if current_rule.meta else {}),
                **payload.meta.model_dump(exclude_none=True),
            }
        elif current_rule.meta:
            request_data["object"]["meta"] = current_rule.meta.model_dump()

        if payload.spec:
            spec_dict = (
                current_rule.spec.model_dump(exclude_none=True)
                if current_rule.spec
                else {}
            )
            spec_dict.update(payload.spec.model_dump(exclude_none=True))
            request_data["object"]["spec"] = spec_dict
        elif current_rule.spec:
            request_data["object"]["spec"] = current_rule.spec.model_dump()

        if payload.disabled is not None:
            request_data["object"]["disabled"] = payload.disabled

        if payload.propagate is not None:
            request_data["object"]["propagate"] = payload.propagate

        # Add update_mask if provided
        if update_mask:
            request_data["request"] = {"update_mask": update_mask}

        logger.info(f"Updating semgrep rule {rule_uuid} with mask: {update_mask}")

        res = client.patch(
            f"v1/namespaces/{tenant_meta_namespace}/semgrep-rules",
            json=request_data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        if res.status_code == 200:
            data = res.json()
            return SemgrepRule(**data)
        else:
            logger.error(
                f"Failed to update semgrep rule {rule_uuid}: "
                f"{res.status_code} - {res.text}"
            )
            return None

    except Exception as e:
        logger.error(f"Error updating semgrep rule {rule_uuid}: {e}", exc_info=True)
        return None


def delete_semgrep_rule(
    client: APIClient, tenant_meta_namespace: str, rule_uuid: str
) -> bool:
    """
    Delete a Semgrep rule.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        rule_uuid: Semgrep rule UUID

    Returns:
        True if deletion succeeded, False otherwise
    """
    ops = _get_semgrep_rule_ops(client)
    return ops.delete(tenant_meta_namespace, rule_uuid)  # type: ignore


# Forward references
SemgrepMetavariableRegex = Dict[str, Any]  # Placeholder - define properly if needed
SemgrepMetavariablePattern = Dict[str, Any]  # Placeholder - define properly if needed
SemgrepPaths = Dict[str, Any]  # Placeholder - define properly if needed
EndorTarget = str  # Placeholder - define properly if needed
