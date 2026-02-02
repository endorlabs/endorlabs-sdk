"""Model validation utilities for Endor Labs resources.

This module provides utilities for safe serialization, partial updates,
and enum validation to handle API evolution gracefully.
"""

import logging
from datetime import datetime
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def safe_serialize(obj: Any) -> Any:
    """Safely serialize objects to JSON-compatible format.

    Handles datetime objects, enums, and other special types that
    can't be directly JSON serialized.

    Args:
        obj: Object to serialize

    Returns:
        JSON-serializable representation of the object

    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, "value"):  # Enum
        return obj.value
    elif hasattr(obj, "model_dump"):  # Pydantic model
        return obj.model_dump()
    elif isinstance(obj, dict):
        return {k: safe_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [safe_serialize(item) for item in obj]
    else:
        return obj


def merge_partial_update(
    existing_data: dict[str, Any],
    update_data: dict[str, Any],
    update_mask: list[str] | None = None,
) -> dict[str, Any]:
    """Merge partial update data with existing data.

    Only updates fields specified in update_mask or non-None fields in update_data.

    Args:
        existing_data: Current resource data
        update_data: New data to merge
        update_mask: Optional list of fields to update

    Returns:
        Merged data dictionary

    """
    result = existing_data.copy()

    if update_mask:
        # Only update specified fields
        for field_path in update_mask:
            _set_nested_field(
                result, field_path, _get_nested_field(update_data, field_path)
            )
    else:
        # Update all non-None fields
        for key, value in update_data.items():
            if value is not None:
                result[key] = value

    return result


def _get_nested_field(data: dict[str, Any], field_path: str) -> Any:
    """Get value from nested field path (e.g., 'spec.level')."""
    keys = field_path.split(".")
    value = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value


def _set_nested_field(data: dict[str, Any], field_path: str, value: Any) -> None:
    """Set value in nested field path (e.g., 'spec.level')."""
    keys = field_path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def validate_enum_value(enum_class: type, value: Any) -> Any:
    """Validate enum value with fallback for unknown values.

    Args:
        enum_class: Enum class to validate against
        value: Value to validate

    Returns:
        Valid enum value or original value if validation fails

    """
    try:
        return enum_class(value)
    except (ValueError, TypeError):
        logger.warning(f"Unknown {enum_class.__name__} value: {value}. Using as-is.")
        return value


def ensure_required_fields(
    data: dict[str, Any], required_fields: list[str], context: str = "validation"
) -> dict[str, Any]:
    """Ensure required fields are present with helpful error messages.

    Args:
        data: Data dictionary to validate
        required_fields: List of required field paths
        context: Context for error messages

    Returns:
        Validated data dictionary

    Raises:
        ValueError: If required fields are missing

    """
    missing_fields = [
        fp for fp in required_fields if _get_nested_field(data, fp) is None
    ]

    if missing_fields:
        raise ValueError(
            f"{context}: Missing required fields: {', '.join(missing_fields)}. "
            f"Please provide all required fields for this operation."
        )

    return data


def create_minimal_payload(model_class: type[T], **kwargs: Any) -> T:
    """Create minimal payload with only provided fields.

    Useful for partial updates where you only want to update specific fields.

    Args:
        model_class: Pydantic model class
        **kwargs: Field values to include

    Returns:
        Model instance with only specified fields

    """
    # Filter out None values
    filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}

    try:
        return model_class(**filtered_kwargs)
    except ValidationError as e:
        logger.error(f"Failed to create {model_class.__name__} payload: {e}")
        raise


def safe_model_dump(
    model: BaseModel, exclude_none: bool = True, exclude_unset: bool = True
) -> dict[str, Any]:
    """Safely dump Pydantic model to dictionary with proper serialization.

    Args:
        model: Pydantic model instance
        exclude_none: Whether to exclude None values
        exclude_unset: Whether to exclude unset values

    Returns:
        Dictionary representation of the model

    """
    try:
        return model.model_dump(
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
            mode="json",  # Use JSON mode for proper serialization
        )
    except Exception as e:
        logger.warning(f"Model dump failed, using safe serialization: {e}")
        # Fallback to manual serialization
        data = {}
        for field_name, field_value in model.__dict__.items():
            if not field_name.startswith("_"):
                data[field_name] = safe_serialize(field_value)
        return data


def validate_update_mask(
    update_mask: str, allowed_fields: list[str], resource_type: str = "resource"
) -> bool:
    """Validate that update_mask only contains allowed fields.

    Args:
        update_mask: Comma-separated list of fields to update
        allowed_fields: List of allowed field paths
        resource_type: Type of resource for error messages

    Returns:
        True if valid, False otherwise

    """
    if not update_mask:
        return True

    fields = [field.strip() for field in update_mask.split(",")]
    invalid_fields = [field for field in fields if field not in allowed_fields]

    if invalid_fields:
        logger.error(
            f"Invalid update_mask for {resource_type}: {invalid_fields}. "
            f"Allowed fields: {allowed_fields}"
        )
        return False

    return True


def get_mutable_fields(resource_type: str) -> list[str]:
    """Get list of mutable fields for a resource type.

    Args:
        resource_type: Type of resource (e.g., 'finding', 'policy')

    Returns:
        List of mutable field paths

    """
    # Define mutable fields for each resource type
    mutable_fields_map = {
        "finding": [
            "meta.tags",
            "spec.finding_tags",
            "spec.dismiss",
            "spec.remediation",
            "context.tags",
        ],
        "policy": [
            "meta.name",
            "meta.description",
            "meta.tags",
            "spec.rule",
            "spec.disable",
            "spec.project_selector",
            "spec.project_exceptions",
            "spec.template_values",
            "propagate",
        ],
        "project": ["meta.description", "meta.tags"],
        "namespace": ["meta.description"],
        "authorization_policy": [
            "meta.name",
            "meta.description",
            "meta.tags",
            "spec",
            "propagate",
        ],
        "scan_profile": ["meta.name", "meta.description", "meta.tags", "spec"],
        "repository": ["meta.name", "meta.description", "meta.tags", "spec"],
        "repository_version": ["meta.name", "meta.description", "meta.tags", "spec"],
        "package_version": ["meta.name", "meta.description", "meta.tags", "spec"],
        "metric": ["meta.name", "meta.description", "meta.tags", "spec"],
        "linter_result": ["meta.name", "meta.description", "meta.tags", "spec"],
        "dependency_metadata": ["meta.name", "meta.description", "meta.tags", "spec"],
        "installation": ["meta.name", "meta.description", "meta.tags", "spec"],
        "package_license": ["meta.name", "meta.description", "meta.tags", "spec"],
        "semgrep_rule": ["meta.name", "meta.description", "meta.tags", "spec"],
        "scan_result": ["meta.name", "meta.description", "meta.tags", "spec"],
    }

    return mutable_fields_map.get(resource_type, [])


# Tag field paths that represent "tags" for .tag()/.untag() capability
TAG_FIELD_PATHS = frozenset({"meta.tags", "spec.finding_tags"})


# Kwarg -> filter path for list() identity kwargs (e.g. name -> meta.name)
LIST_FILTER_KWARG_MAP: dict[str, dict[str, str]] = {
    "project": {"name": "meta.name"},
    "repository": {
        "name": "meta.name",
        "vcs_url": "spec.vcs_url",
        "git_url": "spec.vcs_url",
    },
    "policy": {"name": "meta.name"},
    "namespace": {"name": "meta.name"},
    "scan_profile": {"name": "meta.name"},
    "scan_result": {"name": "meta.name"},
    "finding": {"name": "meta.name"},
}


def get_list_filter_map(resource_type: str) -> dict[str, str]:
    """Return allowed list kwargs and their filter path for this resource type.

    Used by ResourceFacade.list() to build filter from identity kwargs
    (e.g. name='backend' -> meta.name == 'backend').
    """
    if not resource_type:
        return {}
    return dict(LIST_FILTER_KWARG_MAP.get(resource_type, {}))


def build_filter_from_identity_kwargs(
    filter_map: dict[str, str],
    kwargs: dict[str, Any],
) -> tuple[str | None, dict[str, Any]]:
    """Build filter from identity kwargs; return merged filter and remaining kwargs.

    For each kwarg in filter_map that is present in kwargs, builds a clause
    path == 'value' (value quoted). Merges with explicit kwargs.get('filter')
    if present. Returns (merged_filter, remaining_kwargs) with identity keys
    removed from kwargs.
    """
    clauses: list[str] = []
    remaining = dict(kwargs)
    explicit_filter = remaining.pop("filter", None)
    for kwarg, path in filter_map.items():
        if kwarg not in remaining:
            continue
        value = remaining.pop(kwarg)
        if value is None:
            continue
        # Quote string values for API filter syntax
        if isinstance(value, str):
            escaped = value.replace("'", "\\'")
            clause = f"{path} == '{escaped}'"
        else:
            clause = f"{path} == {value!r}"
        clauses.append(clause)
    if not clauses:
        return (explicit_filter, remaining)
    built = " and ".join(f"({c})" for c in clauses)
    if explicit_filter and explicit_filter.strip():
        merged = f"({explicit_filter}) and ({built})"
    else:
        merged = built
    return (merged, remaining)


def get_tags_update_paths(resource_type: str) -> list[str]:
    """Return mutable field paths that represent tags for this resource type.

    Derived from get_mutable_fields: includes meta.tags and/or spec.finding_tags
    when present. Used to expose .tag()/.untag() only on resources that support tags.

    Args:
        resource_type: Type of resource (e.g., 'finding', 'project').

    Returns:
        Tag field paths (e.g. ['meta.tags'], ['meta.tags', 'spec.finding_tags']).

    """
    if not resource_type:
        return []
    mutable = get_mutable_fields(resource_type)
    return [p for p in TAG_FIELD_PATHS if p in mutable]


def get_immutable_fields(resource_type: str) -> list[str]:
    """Get list of immutable fields for a resource type.

    Used by BaseResourceOperations.update() to block PATCH of read-only fields.
    All 16 update-capable resources are in RESOURCE_NAME_TO_TYPE and get this
    check. The 4 original types (finding, policy, project, namespace) have
    spec-derived resource-specific immutable fields; the 12 others use v1Meta-
    derived common set; add resource-specific spec readOnly per-resource from
    OpenAPI when needed.

    Args:
        resource_type: Type of resource (e.g., 'finding', 'policy')

    Returns:
        List of immutable field paths

    """
    # v1Meta readOnly (OpenAPI): create_time, update_time, upsert_time, kind,
    # version, created_by, updated_by, references, index_data
    _v1meta_readonly = [
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
    ]
    # Spec-derived readOnly (OpenAPI Update body object.spec) for 12 resources
    _authz_spec_readonly = ["spec.is_support_policy"]
    _installation_spec_readonly = [
        "spec.external_name",
        "spec.user",
        "spec.ingestion_time",
        "spec.target_type",
        "spec.ingestion_token",
        "spec.marked_for_deletion",
    ]
    _package_version_spec_readonly = [
        "spec.ecosystem",
        "spec.package_name",
        "spec.internal_reference_key",
    ]
    _semgrep_rule_spec_readonly = ["spec.defined_by", "spec.severity_level"]
    immutable_fields_map = {
        "finding": [
            "uuid",
            "meta.name",
            "meta.create_time",
            "meta.created_by",
            "meta.update_time",
            "meta.updated_by",
            "spec.level",
            "spec.project_uuid",
            "spec.finding_metadata",
            "tenant_meta.namespace",
        ],
        "policy": [
            "uuid",
            "meta.create_time",
            "meta.created_by",
            "meta.update_time",
            "meta.updated_by",
            "spec.policy_type",
            "spec.template_uuid",
            "tenant_meta.namespace",
        ],
        "project": [
            "uuid",
            "meta.name",
            "meta.create_time",
            "meta.created_by",
            "meta.update_time",
            "meta.updated_by",
            "spec.git",
            "tenant_meta.namespace",
        ],
        "namespace": [
            "uuid",
            "meta.name",
            "meta.create_time",
            "meta.created_by",
            "meta.update_time",
            "meta.updated_by",
            "tenant_meta.namespace",
        ],
        "authorization_policy": _v1meta_readonly + _authz_spec_readonly,
        "scan_profile": _v1meta_readonly,
        "repository": _v1meta_readonly,
        "repository_version": _v1meta_readonly,
        "package_version": _v1meta_readonly + _package_version_spec_readonly,
        "metric": _v1meta_readonly,
        "linter_result": _v1meta_readonly,
        "dependency_metadata": _v1meta_readonly,
        "installation": _v1meta_readonly + _installation_spec_readonly,
        "package_license": _v1meta_readonly,
        "semgrep_rule": _v1meta_readonly + _semgrep_rule_spec_readonly,
        "scan_result": _v1meta_readonly,
    }

    return immutable_fields_map.get(resource_type, [])
