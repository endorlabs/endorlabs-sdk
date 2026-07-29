"""Build and render executive report packets (HTML + cube JSON)."""

from __future__ import annotations

from endorlabs.workflows.reports.bundles.executive_packet import build_report_packet
from endorlabs.workflows.reports.export.html.render import render_report_packet
from endorlabs.workflows.reports.schemas.packet_v0 import (
    REPORT_PACKET_SCHEMA,
    RUN_BUCKET,
)

__all__ = [
    "REPORT_PACKET_SCHEMA",
    "RUN_BUCKET",
    "build_report_packet",
    "render_report_packet",
]
