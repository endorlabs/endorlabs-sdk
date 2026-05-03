"""Dependency metadata reports and visibility checks."""

from __future__ import annotations

from .reports import check_dependency_visibility, list_project_dependencies
from .types import DependencyReport, DependencyStats, VisibilityReport, VisibilityStats

__all__ = [
    "DependencyReport",
    "DependencyStats",
    "VisibilityReport",
    "VisibilityStats",
    "check_dependency_visibility",
    "list_project_dependencies",
]
