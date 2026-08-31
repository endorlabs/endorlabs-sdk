"""Shared utilities for Endor Labs SDK.

This module provides common utilities used across resource modules to avoid
code duplication while maintaining functionality and type safety.
"""

from .namespace import resolve_namespace_for_resource
from .namespaces import (
    discover_namespace_names,
    list_probe_namespaces,
    namespaces_for_no_traverse_counts,
)
from .parallel import execute_across_namespaces

__all__ = [
    "discover_namespace_names",
    "execute_across_namespaces",
    "list_probe_namespaces",
    "namespaces_for_no_traverse_counts",
    "resolve_namespace_for_resource",
]
