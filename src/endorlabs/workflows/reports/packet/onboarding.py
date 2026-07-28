"""Deprecated shim — use ``endorlabs.workflows.reports.analyze.projects``."""

from __future__ import annotations

import warnings

warnings.warn(
    "endorlabs.workflows.reports.packet.onboarding is deprecated; use "
    "endorlabs.workflows.reports.analyze.projects",
    DeprecationWarning,
    stacklevel=2,
)

from endorlabs.workflows.reports.analyze.projects import (
    build_onboarding_report,
)

__all__ = ["build_onboarding_report"]
