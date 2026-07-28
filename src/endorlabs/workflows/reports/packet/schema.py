"""Deprecated shim — use ``endorlabs.workflows.reports.schemas.packet_v0``."""

from __future__ import annotations

import warnings

warnings.warn(
    "endorlabs.workflows.reports.packet.schema is deprecated; use "
    "endorlabs.workflows.reports.schemas.packet_v0",
    DeprecationWarning,
    stacklevel=2,
)

from endorlabs.workflows.reports.schemas.packet_v0 import *  # noqa: F403
from endorlabs.workflows.reports.schemas.packet_v0 import (
    HIST_KEYS,
    REPORT_PACKET_SCHEMA,
    RUN_BUCKET,
    TagCatalogEntry,
    TagSeriesMeta,
    empty_sprawl_cell,
    hist_bucket,
)

__all__ = [
    "HIST_KEYS",
    "REPORT_PACKET_SCHEMA",
    "RUN_BUCKET",
    "TagCatalogEntry",
    "TagSeriesMeta",
    "empty_sprawl_cell",
    "hist_bucket",
]
