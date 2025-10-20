"""
Validation utilities for Endor Labs resources.

This module provides common validation patterns and utilities
used across all resource modules.
"""

import logging
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class ValidationUtils:
    """Common validation utilities for Endor Labs resources."""
    
    @staticmethod
    def validate_namespace_format(namespace: str) -> bool:
        """
        Validate that namespace follows canonical format.
        
        Args:
            namespace: Namespace string to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not namespace or not isinstance(namespace, str):
            return False
            
        # Check for canonical format: tenant.namespace.child
        parts = namespace.split('.')
        if len(parts) < 2:
            return False
            
        # Each part should be non-empty and contain only valid characters
        for part in parts:
            if not part or not part.replace('-', '').replace('_', '').isalnum():
                return False
                
        return True
    
    @staticmethod
    def validate_uuid_format(uuid: str) -> bool:
        """
        Validate that UUID follows expected format.
        
        Args:
            uuid: UUID string to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not uuid or not isinstance(uuid, str):
            return False
            
        # Basic UUID format validation (24 character alphanumeric)
        return len(uuid) == 24 and uuid.isalnum()
    
    @staticmethod
    def validate_update_mask(update_mask: str, allowed_fields: List[str]) -> bool:
        """
        Validate that update_mask contains only allowed fields.
        
        Args:
            update_mask: Update mask to validate
            allowed_fields: List of allowed field names
            
        Returns:
            True if valid, False otherwise
        """
        if not update_mask or not isinstance(update_mask, str):
            return False
            
        return update_mask in allowed_fields
    
    @staticmethod
    def validate_tags(tags: List[str]) -> bool:
        """
        Validate that tags are properly formatted.
        
        Args:
            tags: List of tags to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(tags, list):
            return False
            
        for tag in tags:
            if not isinstance(tag, str) or not tag.strip():
                return False
                
        return True
    
    @staticmethod
    def sanitize_tags(tags: List[str]) -> List[str]:
        """
        Sanitize tags by removing empty strings and duplicates.
        
        Args:
            tags: List of tags to sanitize
            
        Returns:
            Sanitized list of tags
        """
        if not isinstance(tags, list):
            return []
            
        # Remove empty strings and duplicates, preserve order
        seen = set()
        sanitized = []
        for tag in tags:
            if isinstance(tag, str) and tag.strip() and tag not in seen:
                sanitized.append(tag.strip())
                seen.add(tag)
                
        return sanitized


class ResourceValidator:
    """Resource-specific validation utilities."""
    
    @staticmethod
    def validate_resource_creation(payload: BaseModel, required_fields: List[str]) -> bool:
        """
        Validate that resource creation payload has required fields.
        
        Args:
            payload: Creation payload to validate
            required_fields: List of required field names
            
        Returns:
            True if valid, False otherwise
        """
        try:
            data = payload.model_dump()
            for field in required_fields:
                if field not in data or data[field] is None:
                    logger.warning(f"Missing required field for resource creation: {field}")
                    return False
            return True
        except ValidationError as e:
            logger.error(f"Validation error in resource creation: {e}")
            return False
    
    @staticmethod
    def validate_resource_update(payload: BaseModel, allowed_fields: List[str]) -> bool:
        """
        Validate that resource update payload only contains allowed fields.
        
        Args:
            payload: Update payload to validate
            allowed_fields: List of allowed field names
            
        Returns:
            True if valid, False otherwise
        """
        try:
            data = payload.model_dump(exclude_none=True)
            for field in data.keys():
                if field not in allowed_fields:
                    logger.warning(f"Disallowed field in resource update: {field}")
                    return False
            return True
        except ValidationError as e:
            logger.error(f"Validation error in resource update: {e}")
            return False
