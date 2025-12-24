"""
Shared utilities for Endor Cockpit SDK.

This module provides common utilities used across resource modules to avoid
code duplication while maintaining functionality and type safety.
"""

from .schema_drift import SchemaDriftDetector
from .traversal import create_traverse_params, create_namespace_scoped_params

__all__ = [
    "SchemaDriftDetector",
    "create_traverse_params",
    "create_namespace_scoped_params",
]
