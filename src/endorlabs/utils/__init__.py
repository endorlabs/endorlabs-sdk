"""Shared utilities for Endor Labs SDK.

This module provides common utilities used across resource modules to avoid
code duplication while maintaining functionality and type safety.
"""

from .namespace import resolve_namespace_for_resource
from .parallel import execute_across_namespaces
from .tabular import TabularExport, export_records, records_to_rows, write_table

__all__ = [
    "TabularExport",
    "execute_across_namespaces",
    "export_records",
    "records_to_rows",
    "resolve_namespace_for_resource",
    "write_table",
]
