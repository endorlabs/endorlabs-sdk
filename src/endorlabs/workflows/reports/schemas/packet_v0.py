"""Schema constants for executive report packets."""

from __future__ import annotations

from typing import Any, TypedDict

REPORT_PACKET_SCHEMA = "endor.report_packet.v0"
RUN_BUCKET = "executive-report-packet"
# Campaign / patches-only outputs (``endor-reports packet --patches-only``).
PATCHES_RUN_BUCKET = "patches-reports"

HIST_KEYS: tuple[str, ...] = ("1", "2-3", "4-5", "6-10", "11-25", "26+")


class TagCatalogEntry(TypedDict):
    tag: str
    projectCount: int
    projectUuids: list[str]


class TagSeriesMeta(TypedDict):
    seriesReady: list[str]
    seriesPending: list[str]
    seriesReadyCount: int
    seriesPendingCount: int
    pullPolicy: dict[str, Any]


def empty_sprawl_cell() -> dict[str, Any]:
    """Empty version-sprawl aggregate cell."""
    return {
        "p": 0,
        "v": 0,
        "max": 0,
        "avg": 0.0,
        "h": [0, 0, 0, 0, 0, 0],
        "hv": [0, 0, 0, 0, 0, 0],
        "t": [],
    }


def hist_bucket(n: int) -> str:
    """Map distinct version count to a sprawl histogram key."""
    if n <= 1:
        return "1"
    if n <= 3:
        return "2-3"
    if n <= 5:
        return "4-5"
    if n <= 10:
        return "6-10"
    if n <= 25:
        return "11-25"
    return "26+"
