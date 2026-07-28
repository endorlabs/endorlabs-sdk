"""Deprecated shim — use ``endorlabs.workflows.reports.analyze.projects``."""

from __future__ import annotations

import warnings

warnings.warn(
    "endorlabs.workflows.reports.packet.discover is deprecated; use "
    "endorlabs.workflows.reports.analyze.projects",
    DeprecationWarning,
    stacklevel=2,
)

from endorlabs.workflows.reports.analyze.projects import (
    discover_projects,
    normalize_project_row,
    path_options_from_namespaces,
)

__all__ = [
    "discover_projects",
    "normalize_project_row",
    "path_options_from_namespaces",
]
