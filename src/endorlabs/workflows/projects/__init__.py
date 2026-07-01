"""Project discovery helpers for workflow orchestration."""

from __future__ import annotations

from .discovery import duplicate_project_decision, resolve_project_candidate
from .inventory import (
    INSTALLATION_LIST_MASK,
    build_installation_lookup,
    fetch_installation_lookup,
    installation_display_name,
)

__all__ = [
    "INSTALLATION_LIST_MASK",
    "build_installation_lookup",
    "duplicate_project_decision",
    "fetch_installation_lookup",
    "installation_display_name",
    "resolve_project_candidate",
]
