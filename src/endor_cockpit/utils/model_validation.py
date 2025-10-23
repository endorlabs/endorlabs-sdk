"""
Model validation utilities for Endor Labs resources.

This module provides utilities for safe serialization, partial updates,
and enum validation to handle API evolution gracefully.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def safe_serialize(obj: Any) -> Any:
    """
    Safely serialize objects to JSON-compatible format.
    
    Handles datetime objects, enums, and other special types that
    can't be directly JSON serialized.
    
    Args:
        obj: Object to serialize
        
    Returns:
        JSON-serializable representation of the object
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, 'value'):  # Enum
        return obj.value
    elif hasattr(obj, 'model_dump'):  # Pydantic model
        return obj.model_dump()
    elif isinstance(obj, dict):
        return {k: safe_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [safe_serialize(item) for item in obj]
    else:
        return obj


def merge_partial_update(
    existing_data: Dict[str, Any],
    update_data: Dict[str, Any],
    update_mask: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Merge partial update data with existing data.
    
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
            _set_nested_field(result, field_path, _get_nested_field(update_data, field_path))
    else:
        # Update all non-None fields
        for key, value in update_data.items():
            if value is not None:
                result[key] = value

    return result


def _get_nested_field(data: Dict[str, Any], field_path: str) -> Any:
    """Get value from nested field path (e.g., 'spec.level')."""
    keys = field_path.split('.')
    value = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value


def _set_nested_field(data: Dict[str, Any], field_path: str, value: Any) -> None:
    """Set value in nested field path (e.g., 'spec.level')."""
    keys = field_path.split('.')
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def validate_enum_value(enum_class: Type, value: Any) -> Any:
    """
    Validate enum value with fallback for unknown values.
    
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
    data: Dict[str, Any],
    required_fields: List[str],
    context: str = "validation"
) -> Dict[str, Any]:
    """
    Ensure required fields are present with helpful error messages.
    
    Args:
        data: Data dictionary to validate
        required_fields: List of required field paths
        context: Context for error messages
        
    Returns:
        Validated data dictionary
        
    Raises:
        ValueError: If required fields are missing
    """
    missing_fields = []

    for field_path in required_fields:
        if _get_nested_field(data, field_path) is None:
            missing_fields.append(field_path)

    if missing_fields:
        raise ValueError(
            f"{context}: Missing required fields: {', '.join(missing_fields)}. "
            f"Please provide all required fields for this operation."
        )

    return data


def create_minimal_payload(
    model_class: Type[T],
    **kwargs
) -> T:
    """
    Create minimal payload with only provided fields.
    
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
    model: BaseModel,
    exclude_none: bool = True,
    exclude_unset: bool = True
) -> Dict[str, Any]:
    """
    Safely dump Pydantic model to dictionary with proper serialization.
    
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
            mode='json'  # Use JSON mode for proper serialization
        )
    except Exception as e:
        logger.warning(f"Model dump failed, using safe serialization: {e}")
        # Fallback to manual serialization
        data = {}
        for field_name, field_value in model.__dict__.items():
            if not field_name.startswith('_'):
                data[field_name] = safe_serialize(field_value)
        return data


def validate_update_mask(
    update_mask: str,
    allowed_fields: List[str],
    resource_type: str = "resource"
) -> bool:
    """
    Validate that update_mask only contains allowed fields.
    
    Args:
        update_mask: Comma-separated list of fields to update
        allowed_fields: List of allowed field paths
        resource_type: Type of resource for error messages
        
    Returns:
        True if valid, False otherwise
    """
    if not update_mask:
        return True

    fields = [field.strip() for field in update_mask.split(',')]
    invalid_fields = [field for field in fields if field not in allowed_fields]

    if invalid_fields:
        logger.error(
            f"Invalid update_mask for {resource_type}: {invalid_fields}. "
            f"Allowed fields: {allowed_fields}"
        )
        return False

    return True


def get_mutable_fields(resource_type: str) -> List[str]:
    """
    Get list of mutable fields for a resource type.
    
    Args:
        resource_type: Type of resource (e.g., 'finding', 'policy')
        
    Returns:
        List of mutable field paths
    """
    # Define mutable fields for each resource type
    mutable_fields_map = {
        'finding': [
            'meta.tags',
            'spec.finding_tags',
            'spec.dismiss',
            'spec.remediation',
            'context.tags'
        ],
        'policy': [
            'meta.name',
            'meta.description',
            'meta.tags',
            'spec.rule',
            'spec.disable',
            'spec.project_selector',
            'spec.project_exceptions',
            'spec.template_values',
            'propagate'
        ],
        'project': [
            'meta.description',
            'meta.tags'
        ],
        'namespace': [
            'meta.description'
        ]
    }

    return mutable_fields_map.get(resource_type, [])


def get_immutable_fields(resource_type: str) -> List[str]:
    """
    Get list of immutable fields for a resource type.
    
    Args:
        resource_type: Type of resource (e.g., 'finding', 'policy')
        
    Returns:
        List of immutable field paths
    """
    # Define immutable fields for each resource type
    immutable_fields_map = {
        'finding': [
            'uuid',
            'meta.name',
            'meta.create_time',
            'meta.created_by',
            'meta.update_time',
            'meta.updated_by',
            'spec.level',
            'spec.project_uuid',
            'spec.finding_metadata',
            'tenant_meta.namespace'
        ],
        'policy': [
            'uuid',
            'meta.create_time',
            'meta.created_by',
            'meta.update_time',
            'meta.updated_by',
            'spec.policy_type',
            'spec.template_uuid',
            'tenant_meta.namespace'
        ],
        'project': [
            'uuid',
            'meta.name',
            'meta.create_time',
            'meta.created_by',
            'meta.update_time',
            'meta.updated_by',
            'spec.git',
            'tenant_meta.namespace'
        ],
        'namespace': [
            'uuid',
            'meta.name',
            'meta.create_time',
            'meta.created_by',
            'meta.update_time',
            'meta.updated_by',
            'tenant_meta.namespace'
        ]
    }

    return immutable_fields_map.get(resource_type, [])
