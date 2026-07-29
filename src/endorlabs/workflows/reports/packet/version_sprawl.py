"""Deprecated shim — use ``endorlabs.workflows.reports.analyze.sprawl``."""

from __future__ import annotations

import warnings

warnings.warn(
    "endorlabs.workflows.reports.packet.version_sprawl is deprecated; use "
    "endorlabs.workflows.reports.analyze.sprawl",
    DeprecationWarning,
    stacklevel=2,
)

from endorlabs.workflows.reports.analyze.sprawl import (
    build_version_sprawl_report,
    collect_leaf_pairs,
)

__all__ = ["build_version_sprawl_report", "collect_leaf_pairs"]
