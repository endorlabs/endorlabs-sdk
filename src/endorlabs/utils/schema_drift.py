"""Schema drift detection utilities for Endor Labs API.

This module provides utilities for detecting and logging API schema drift,
which occurs when the API returns fields that are not defined in our
Pydantic models. This is common during API evolution and helps maintain
backward compatibility.
"""

from typing import Any

# Set up logger for schema drift detection
from .logging_config import get_resource_logger

logger = get_resource_logger(__name__)


class SchemaDriftDetector:
    """Detects and logs API schema drift for unknown fields.

    This class provides static methods to identify and log unknown fields
    in API responses, helping developers track API evolution and identify
    missing model fields.
    """

    @staticmethod
    def log_unknown_fields(
        model_name: str,
        unknown_fields: dict[str, Any],
        context: str = "",
        resource_name: str | None = None,
    ) -> None:
        """Log unknown fields as warnings for schema drift detection.

        Args:
            model_name: Name of the model where drift was detected
            unknown_fields: Dictionary of unknown field names and values
            context: Additional context about where the drift occurred
            resource_name: Name of the resource (e.g., "Finding", "Policy") for context

        """
        # Suppress known ignored fields that are expected in API responses
        known_ignored_fields = {
            "tenant",
            "data",
            "will_be_deleted_at",
            "search_score",
            "scan_time",
        }
        filtered_unknown_fields = {
            k: v for k, v in unknown_fields.items() if k not in known_ignored_fields
        }

        if filtered_unknown_fields:
            field_list = ", ".join(filtered_unknown_fields.keys())
            # Include resource name in log message if provided
            if resource_name:
                log_message = (
                    f"API Schema Drift Detected in {resource_name}.{model_name}: "
                    f"Unknown fields found: {field_list}"
                )
            else:
                log_message = (
                    f"API Schema Drift Detected in {model_name}: "
                    f"Unknown fields found: {field_list}"
                )
            if context:
                log_message += f". Context: {context}"
            log_message += ". This may indicate API evolution or missing model fields."
            logger.warning(log_message)
            # Log detailed field information for debugging
            for field, value in unknown_fields.items():
                logger.debug(
                    "Unknown field '%s': %s = %s",
                    field,
                    type(value).__name__,
                    repr(value)[:100],
                )

    @staticmethod
    def extract_unknown_fields(
        data: dict[str, Any],
        model_fields: set[str],
        model_name: str,
        resource_name: str | None = None,
    ) -> dict[str, Any]:
        """Extract unknown fields from data and log them.

        Args:
            data: Dictionary containing the data to check
            model_fields: Set of known field names for the model
            model_name: Name of the model for logging purposes
            resource_name: Name of the resource (e.g., "Finding", "Policy") for context

        Returns:
            Dictionary of unknown fields and their values

        """
        unknown_fields = {k: v for k, v in data.items() if k not in model_fields}
        if unknown_fields:
            SchemaDriftDetector.log_unknown_fields(
                model_name, unknown_fields, resource_name=resource_name
            )
        return unknown_fields

    @staticmethod
    def create_field_validator(
        model_fields: set[str], model_name: str, resource_name: str | None = None
    ) -> Any:
        """Create a Pydantic field validator for schema drift detection.

        This method returns a validator function that can be used with
        Pydantic's @field_validator decorator to automatically detect
        schema drift in model fields.

        Args:
            model_fields: Set of known field names for the model
            model_name: Name of the model for logging purposes
            resource_name: Name of the resource (e.g., "Finding", "Policy") for context

        Returns:
            Validator function for use with @field_validator

        """

        def validator(v: Any, info: Any) -> Any:
            """Detect and log schema drift for unknown fields."""
            if info.field_name and isinstance(v, dict):
                _ = SchemaDriftDetector.extract_unknown_fields(
                    v,
                    model_fields,
                    f"{model_name}.{info.field_name}",
                    resource_name=resource_name,
                )
            return v

        return validator
