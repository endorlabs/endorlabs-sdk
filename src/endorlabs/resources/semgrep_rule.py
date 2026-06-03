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

from typing import Any, ClassVar, override

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
    FlexibleEnum,
)
from ..utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)


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


class SemgrepPaths(BaseModel):
    """Semgrep rule path inclusion/exclusion (v1SemgrepPaths)."""

    model_config = ConfigDict(extra="allow")

    include: list[str] | None = Field(None, description="Path inclusion patterns")
    exclude: list[str] | None = Field(None, description="Path exclusion patterns")


class SemgrepOptions(BaseModel):
    """Semgrep rule options (v1SemgrepOptions)."""

    model_config = ConfigDict(extra="allow")

    symbolic_propagation: bool | None = Field(
        None, description="Enable symbolic propagation"
    )
    interfile: bool | None = Field(None, description="Enable interfile analysis")
    assume_numbers_are_safe: bool | None = Field(
        None,
        alias="taint_assume_safe_numbers",
        description="Assume numbers are safe",
    )
    taint_unify_mvars: bool | None = Field(
        None, description="Enable unification of metavariables in taint analysis"
    )
    generic_ellipsis_max_span: int | None = Field(
        None, description="Maximum span for generic ellipsis patterns"
    )
    taint_assume_safe_booleans: bool | None = Field(
        None, description="Assume boolean values are safe in taint analysis"
    )
    taint_assume_safe_functions: bool | None = Field(
        None, description="Assume function calls are safe in taint analysis"
    )
    constant_propagation: bool | None = Field(
        None, description="Enable constant propagation analysis"
    )
    implicit_deep_exprstmt: bool | None = Field(
        None, description="Enable implicit deep expression statement analysis"
    )
    generic_engine: str | None = Field(
        None, description="Generic engine to use for analysis"
    )


class SemgrepRulePatternType(BaseModel):
    """Semgrep rule pattern type (v1SemgrepRulePatternType, recursive structure)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

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
    pattern_inside: str | None = Field(None, description="Pattern inside")
    pattern_not_inside: str | None = Field(None, description="Pattern not inside")
    metavariable_pattern: SemgrepMetavariablePattern | None = Field(
        None, description="Metavariable pattern"
    )
    metavariable_analysis: dict[str, Any] | None = Field(
        None, description="Metavariable analysis"
    )
    metavariable_comparison: dict[str, Any] | None = Field(
        None, description="Metavariable comparison"
    )
    metavariable_type: dict[str, Any] | None = Field(
        None, description="Metavariable type"
    )
    pattern_either_new: list[SemgrepRulePatternType] | None = Field(
        None, description="Pattern either (new-style)"
    )
    focus_metavariable: list[str] | None = Field(
        None, description="Focus metavariables"
    )
    exact: bool | None = Field(None, description="Exact match")
    by_side_effect: bool | None = Field(None, description="By side effect")
    label: str | None = Field(None, description="Pattern label")
    requires: str | None = Field(None, description="Label requirement expression")
    not_conflicting: bool | None = Field(None, description="Not conflicting flag")
    management: dict[str, Any] | None = Field(None, description="Management config")
    pattern_inside_either: list[SemgrepRulePatternType] | None = Field(
        None, description="Pattern inside either list"
    )


class SemgrepRuleMeta(BaseModel):
    """Semgrep rule metadata (v1SemgrepRuleMeta).

    All fields are optional. ``extra="allow"`` ensures forward
    compatibility when the API adds new metadata fields.
    """

    model_config = ConfigDict(extra="allow")

    # --- Fields present in the original SDK model ---
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

    # --- Fields added from v1SemgrepRuleMeta API spec ---
    endor_category: str | None = Field(
        None, description="Rule purpose (vulnerability, malware-detection, etc.)"
    )
    endor_tags: list[str] | None = Field(
        None, description="Generic tags controlling later processing of rule results"
    )
    endor_attack_examples: list[str] | None = Field(
        None, description="References to attack descriptions"
    )
    endor_rule_origin: dict[str, Any] | None = Field(
        None, description="Rule origin metadata (license, URL)"
    )
    version: str | None = Field(None, description="Semantic version of the rule")
    security_severity: str | None = Field(None, description="Security severity score")
    short_description: str | None = Field(None, description="Short rule description")
    explanation: str | None = Field(None, description="Extended explanation")
    remediation: str | None = Field(None, description="Remediation guidance")
    author: str | None = Field(None, description="Rule author")
    vulnerability: str | None = Field(None, description="Vulnerability identifier")
    severity: str | None = Field(None, description="Severity string")
    help: str | None = Field(None, description="Help text")
    precision: str | None = Field(None, description="Rule precision")
    tags: list[str] | None = Field(None, description="Generic tags")
    functional_categories: list[str] | None = Field(
        None, description="Functional categories"
    )
    vulnerability_class: list[str] | None = Field(
        None, description="Vulnerability class"
    )
    deprecated: bool | None = Field(None, description="Whether rule is deprecated")
    display_name: str | None = Field(None, description="Display name")
    cwe2023_top25: bool | None = Field(None, description="CWE 2023 Top 25 flag")
    cwe2020_top25: bool | None = Field(None, description="CWE 2020 Top 25 flag")
    interfile: bool | None = Field(None, description="Interfile analysis flag")
    masvs: list[str] | None = Field(
        None, description="Mobile Application Security Verification Standard"
    )
    resources: list[str] | None = Field(None, description="Resource references")
    rule_origin_note: str | None = Field(None, description="Rule origin note")
    source_url_open: str | None = Field(None, description="Open source URL")
    bandit_code: str | None = Field(None, description="Bandit code reference")
    owaspapi: str | None = Field(None, description="OWASP API category")


class SemgrepNativeRule(BaseModel):
    """Semgrep native rule (v1SemgrepNativeRule, Semgrep-compatible)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

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

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift in semgrep rule responses."""
        _ = info  # Reserved for future drift logging; matches BaseResource signature.
        return v

    @override
    @classmethod
    def get_mutable_fields_cls(cls) -> list[str]:
        """Get list of mutable fields for SemgrepRule."""
        return ["meta.name", "meta.description", "meta.tags", "spec"]

    @override
    @classmethod
    def get_immutable_fields_cls(cls) -> list[str]:
        """Get list of immutable fields for SemgrepRule."""
        return [
            "uuid",
            "meta.create_time",
            "meta.created_by",
            "meta.update_time",
            "meta.updated_by",
            "meta.upsert_time",
            "meta.kind",
            "meta.version",
            "meta.references",
            "meta.index_data",
            "tenant_meta.namespace",
            "spec.defined_by",
            "spec.severity_level",
        ]


def _rule_to_yaml(rule: SemgrepNativeRule) -> str:
    """Build minimal Semgrep rule YAML so the API can parse the rule.

    The Endor Labs API expects ``spec.yaml`` when creating rules. This
    helper converts a ``SemgrepNativeRule`` object to a clean YAML
    string, omitting ``None`` fields that would cause unmarshal errors.
    """
    entry: dict[str, Any] = {}
    if rule.id:
        entry["id"] = rule.id
    if rule.pattern:
        entry["pattern"] = rule.pattern
    if rule.message:
        entry["message"] = rule.message
    if rule.languages:
        entry["languages"] = rule.languages
    if rule.severity:
        entry["severity"] = rule.severity
    if rule.mode:
        entry["mode"] = rule.mode
    return yaml.dump({"rules": [entry]}, default_flow_style=False, allow_unicode=True)


class CreateSemgrepRulePayload(BaseModel):
    """Payload for creating a new Semgrep rule.

    When ``spec.rule`` is provided but ``spec.yaml`` is not, the YAML
    representation is auto-generated so the API can parse the rule.
    """

    meta: SemgrepRuleMetaCreate = Field(..., description="Semgrep rule metadata")
    spec: SemgrepRuleSpec = Field(..., description="Semgrep rule specification")
    propagate: bool | None = Field(True, description="Propagate to child namespaces")
    disabled: bool | None = Field(None, description="Whether rule is disabled")

    @model_validator(mode="after")
    def _auto_generate_yaml(self) -> CreateSemgrepRulePayload:
        """Generate spec.yaml from spec.rule when not provided."""
        if self.spec and self.spec.rule and not self.spec.yaml:
            self.spec = self.spec.model_copy(
                update={"yaml": _rule_to_yaml(self.spec.rule)}
            )
        return self


def build_create_payload(**kwargs: Any) -> CreateSemgrepRulePayload:
    """Build CreateSemgrepRulePayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateSemgrepRulePayload, kwargs, attr_name="SemgrepRule"
    )


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


_PATTERN_KEYS = frozenset(
    {
        "pattern",
        "patterns",
        "pattern_either",
        "pattern_sources",
        "pattern_sinks",
        "pattern_regex",
    }
)


def _validate_patterns(rule: Any, errors: list[str]) -> None:
    """Validate pattern types.

    Checks both explicit model fields and ``model_extra`` so that
    compound-pattern rules whose pattern keys landed in extra still pass.
    """
    has_patterns = (
        rule.pattern is not None
        or (rule.patterns and len(rule.patterns) > 0)
        or (rule.pattern_either and len(rule.pattern_either) > 0)
        or (rule.pattern_sources and len(rule.pattern_sources) > 0)
        or (rule.pattern_sinks and len(rule.pattern_sinks) > 0)
        or rule.pattern_regex is not None
    )

    # Also check model_extra for pattern keys (extra="allow" may store them there)
    if not has_patterns and hasattr(rule, "model_extra") and rule.model_extra:
        for key in _PATTERN_KEYS:
            val = rule.model_extra.get(key)
            if val is not None:
                has_patterns = True
                break

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


# Forward references
SemgrepMetavariableRegex = dict[str, Any]  # Placeholder - define properly if needed
SemgrepMetavariablePattern = dict[str, Any]  # Placeholder - define properly if needed
EndorTarget = str  # Placeholder - define properly if needed
