"""
Data models for Endor Labs resources.

This module provides Pydantic models for all Endor Labs resources,
following a consistent pattern for type safety and validation.
"""

from .base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
    Context,
    IngestedObject,
    ProcessingStatus,
    TenantMeta,
)

__all__ = [
    # Base classes
    "BaseResource",
    "BaseMeta",
    "BaseSpec",
    "TenantMeta",
    # Conditional attribute models
    "Context",
    "ProcessingStatus",
    "IngestedObject",
]
