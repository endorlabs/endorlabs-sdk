"""Shared utilities for Endor Cockpit SDK.

This module provides common utilities used across resource modules to avoid
code duplication while maintaining functionality and type safety.
"""

from .namespace import resolve_namespace_for_resource
from .parallel import execute_across_namespaces
from .schema_drift import SchemaDriftDetector

__all__ = [
    "SchemaDriftDetector",
    "execute_across_namespaces",
    "resolve_namespace_for_resource",
]
