"""Deprecated shim — use ``endorlabs.workflows.reports.bundles.executive_packet``."""

from __future__ import annotations

import warnings

warnings.warn(
    "endorlabs.workflows.reports.packet.build is deprecated; use "
    "endorlabs.workflows.reports.bundles.executive_packet",
    DeprecationWarning,
    stacklevel=2,
)

from endorlabs.workflows.reports.bundles.executive_packet import (
    build_report_packet,
)

__all__ = ["build_report_packet"]
