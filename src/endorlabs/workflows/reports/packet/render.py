"""Deprecated shim — use ``endorlabs.workflows.reports.export.html.render``."""

from __future__ import annotations

import warnings

warnings.warn(
    "endorlabs.workflows.reports.packet.render is deprecated; use "
    "endorlabs.workflows.reports.export.html.render",
    DeprecationWarning,
    stacklevel=2,
)

from endorlabs.workflows.reports.export.html.render import (
    default_packet_output_dir,
    render_report_packet,
)

__all__ = ["default_packet_output_dir", "render_report_packet"]
