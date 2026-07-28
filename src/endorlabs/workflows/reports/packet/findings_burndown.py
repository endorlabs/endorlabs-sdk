"""Deprecated shim — use ``endorlabs.workflows.reports.analyze.findings_trend``."""

from __future__ import annotations

import warnings

warnings.warn(
    "endorlabs.workflows.reports.packet.findings_burndown is deprecated; use "
    "endorlabs.workflows.reports.analyze.findings_trend",
    DeprecationWarning,
    stacklevel=2,
)

from endorlabs.workflows.reports.analyze.findings_trend import (
    build_findings_burndown_report,
    build_sca_burndown_report,
)

__all__ = ["build_findings_burndown_report", "build_sca_burndown_report"]
