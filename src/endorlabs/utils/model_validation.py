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


def parse_update_mask(update_mask: str) -> list[str]:
    """Parse comma-separated update_mask string into a list of field paths.

    Splits on comma, strips whitespace, and drops empty entries.

    Args:
        update_mask: Comma-separated field paths (e.g. "meta.description, meta.tags").

    Returns:
        List of non-empty trimmed paths.

    """
    if not update_mask:
        return []
    return [p.strip() for p in update_mask.split(",") if p.strip()]


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

    fields = parse_update_mask(update_mask)
    invalid_fields = [field for field in fields if field not in allowed_fields]

    if invalid_fields:
        logger.error(
            f"Invalid update_mask for {resource_type}: {invalid_fields}. "
            f"Allowed fields: {allowed_fields}"
        )
        return False

    return True


# Tag field paths that represent "tags" for .tag()/.untag() capability
TAG_FIELD_PATHS = frozenset({"meta.tags", "spec.finding_tags"})


def get_tags_update_paths(model_class: type) -> list[str]:
    """Return mutable field paths that represent tags for this resource type.

    Derived from the model's get_mutable_fields_cls(): includes meta.tags
    and/or spec.finding_tags when present. Used to expose .tag()/.untag()
    only on resources that support tags.

    Args:
        model_class: Resource model class (e.g. Project, Finding) with
            get_mutable_fields_cls() classmethod.

    Returns:
        Tag field paths (e.g. ['meta.tags'], ['meta.tags', 'spec.finding_tags']).

    """
    if not hasattr(model_class, "get_mutable_fields_cls"):
        return []
    mutable = model_class.get_mutable_fields_cls()
    return [p for p in TAG_FIELD_PATHS if p in mutable]


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
    "authorization_policy": {"name": "meta.name"},
    "repository_version": {"name": "meta.name"},
    "installation": {"name": "meta.name"},
    "notification_target": {"name": "meta.name"},
    "metric": {"name": "meta.name"},
    "semgrep_rule": {"name": "meta.name"},
    "package_version": {"name": "meta.name"},
    "invitation": {"name": "meta.name"},
    "code_owners": {"name": "meta.name"},
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
    ``path == value`` using the ``F()`` filter builder for safe escaping.
    Merges with explicit ``kwargs.get('filter')`` if present. Returns
    ``(merged_filter, remaining_kwargs)`` with identity keys removed.
    """
    from ..filter import F, FilterExpression

    clauses: list[FilterExpression] = []
    remaining = dict(kwargs)
    explicit_filter = remaining.pop("filter", None)
    for kwarg, path in filter_map.items():
        if kwarg not in remaining:
            continue
        value = remaining.pop(kwarg)
        if value is None:
            continue
        clauses.append(F(path) == value)
    if not clauses:
        return (explicit_filter, remaining)
    # Join clauses with AND: "(clause1) and (clause2) and ..."
    built = " and ".join(f"({c})" for c in clauses)
    if explicit_filter and str(explicit_filter).strip():
        merged = f"({explicit_filter}) and ({built})"
    else:
        merged = built
    return (merged, remaining)
