"""Shared utilities for Endor Cockpit SDK.

This module provides common utilities used across resource modules to avoid
code duplication while maintaining functionality and type safety.
"""

from .namespace import resolve_namespace_for_resource
from .parallel import execute_across_namespaces
from .schema_drift import SchemaDriftDetector
from .traversal import create_namespace_scoped_params, create_traverse_params

__all__ = [
    "SchemaDriftDetector",
    "create_namespace_scoped_params",
    "create_traverse_params",
    "execute_across_namespaces",
    "resolve_namespace_for_resource",
]
