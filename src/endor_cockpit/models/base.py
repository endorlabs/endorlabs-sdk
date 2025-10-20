"""
Base model classes for Endor Labs resources.

This module provides base classes that define the common patterns
used across all Endor Labs resource models.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..utils import SchemaDriftDetector

logger = logging.getLogger(__name__)


class TenantMeta(BaseModel):
    """Base tenant metadata for all resources."""
    namespace: str = Field(..., description="Canonical namespace name")


class BaseMeta(BaseModel):
    """Base metadata for all resources."""
    name: str = Field(..., description="Resource name")
    description: Optional[str] = Field(None, description="Resource description")
    create_time: Optional[str] = Field(None, description="Creation timestamp")
    created_by: Optional[str] = Field(None, description="Creator identifier")
    update_time: Optional[str] = Field(None, description="Last update timestamp")
    updated_by: Optional[str] = Field(None, description="Last updater identifier")
    tags: Optional[List[str]] = Field(None, description="Resource tags")
    
    # Schema drift fields
    parent_uuid: Optional[str] = Field(None, description="Parent resource UUID")
    parent_kind: Optional[str] = Field(None, description="Parent resource kind")
    upsert_time: Optional[str] = Field(None, description="Upsert timestamp")
    references: Optional[Dict[str, Any]] = Field(None, description="Resource references")

    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            model_fields = {
                'create_time', 'update_time', 'name', 'description', 'created_by', 
                'updated_by', 'tags', 'parent_uuid', 'parent_kind', 'upsert_time', 'references'
            }
            
            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields, f"BaseMeta.{info.field_name}"
                )
        return v


class BaseSpec(BaseModel):
    """Base specification for all resources."""
    model_config = ConfigDict(extra='ignore')
    
    # Schema drift fields
    notification: Optional[Dict[str, Any]] = Field(None, description="Notification configuration")

    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            model_fields = {'notification'}
            
            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields, f"BaseSpec.{info.field_name}"
                )
        return v


class BaseResource(BaseModel):
    """Base resource model for all Endor Labs resources."""
    model_config = ConfigDict(extra='ignore')
    
    uuid: str = Field(..., description="Unique identifier for the resource")
    meta: BaseMeta = Field(..., description="Resource metadata")
    spec: BaseSpec = Field(..., description="Resource specification")
    tenant_meta: TenantMeta = Field(..., description="Tenant metadata")

    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            model_fields = {'uuid', 'meta', 'spec', 'tenant_meta'}
            
            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields, f"BaseResource.{info.field_name}"
                )
        return v

    def get_mutable_fields(self) -> List[str]:
        """Get list of mutable fields for this resource."""
        return ["meta.description", "meta.tags"]

    def get_immutable_fields(self) -> List[str]:
        """Get list of immutable fields for this resource."""
        return [
            "uuid", "meta.name", "meta.create_time", "meta.created_by",
            "meta.update_time", "meta.updated_by", "tenant_meta.namespace"
        ]

    def validate_update_mask(self, update_mask: str) -> bool:
        """Validate that update_mask only contains mutable fields."""
        mutable_fields = self.get_mutable_fields()
        return update_mask in mutable_fields
