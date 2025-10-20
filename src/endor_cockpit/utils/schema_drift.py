"""
Schema drift detection utilities for Endor Labs API.

This module provides utilities for detecting and logging API schema drift,
which occurs when the API returns fields that are not defined in our
Pydantic models. This is common during API evolution and helps maintain
backward compatibility.
"""

import logging
from typing import Dict, Set

# Set up logger for schema drift detection
logger = logging.getLogger(__name__)


class SchemaDriftDetector:
    """
    Detects and logs API schema drift for unknown fields.
    
    This class provides static methods to identify and log unknown fields
    in API responses, helping developers track API evolution and identify
    missing model fields.
    """

    @staticmethod
    def log_unknown_fields(model_name: str, unknown_fields: Dict[str, any], context: str = "") -> None:
        """
        Log unknown fields as warnings for schema drift detection.
        
        Args:
            model_name: Name of the model where drift was detected
            unknown_fields: Dictionary of unknown field names and values
            context: Additional context about where the drift occurred
        """
        if unknown_fields:
            field_list = ", ".join(unknown_fields.keys())
            logger.warning(
                f"API Schema Drift Detected in {model_name}: "
                f"Unknown fields found: {field_list}. "
                f"Context: {context}. "
                f"This may indicate API evolution or missing model fields."
            )
            # Log detailed field information for debugging
            for field, value in unknown_fields.items():
                logger.debug(
                    f"Unknown field '{field}': {type(value).__name__} = "
                    f"{repr(value)[:100]}"
                )

    @staticmethod
    def extract_unknown_fields(data: Dict[str, any], model_fields: Set[str], model_name: str) -> Dict[str, any]:
        """
        Extract unknown fields from data and log them.
        
        Args:
            data: Dictionary containing the data to check
            model_fields: Set of known field names for the model
            model_name: Name of the model for logging purposes
            
        Returns:
            Dictionary of unknown fields and their values
        """
        unknown_fields = {k: v for k, v in data.items() if k not in model_fields}
        if unknown_fields:
            SchemaDriftDetector.log_unknown_fields(model_name, unknown_fields)
        return unknown_fields

    @staticmethod
    def create_field_validator(model_fields: Set[str], model_name: str):
        """
        Create a Pydantic field validator for schema drift detection.
        
        This method returns a validator function that can be used with
        Pydantic's @field_validator decorator to automatically detect
        schema drift in model fields.
        
        Args:
            model_fields: Set of known field names for the model
            model_name: Name of the model for logging purposes
            
        Returns:
            Validator function for use with @field_validator
        """
        def validator(v, info):
            """Detect and log schema drift for unknown fields."""
            if info.field_name and isinstance(v, dict):
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields, f"{model_name}.{info.field_name}"
                )
            return v
        
        return validator
