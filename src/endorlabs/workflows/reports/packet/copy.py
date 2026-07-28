"""Deprecated shim — use ``endorlabs.workflows.reports.export.html.copy``."""

from __future__ import annotations

import warnings

warnings.warn(
    "endorlabs.workflows.reports.packet.copy is deprecated; use "
    "endorlabs.workflows.reports.export.html.copy",
    DeprecationWarning,
    stacklevel=2,
)

from endorlabs.workflows.reports.export.html.copy import *  # noqa: F403
