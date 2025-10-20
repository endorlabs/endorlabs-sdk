"""
Shared utilities for Endor Cockpit SDK.

This module provides common utilities used across resource modules to avoid
code duplication while maintaining functionality and type safety.
"""

from .schema_drift import SchemaDriftDetector

__all__ = ["SchemaDriftDetector"]
