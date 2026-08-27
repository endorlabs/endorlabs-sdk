"""Shared half-open time-window helpers for log list/count filters."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta


def parse_iso_utc(value: str) -> datetime:
    """Parse an ISO-8601 timestamp into an aware UTC datetime."""
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    parsed = datetime.fromisoformat(cleaned)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def format_mql_date(value: datetime) -> str:
    """Format a datetime for Endor MQL ``date(...)`` filters (UTC Z)."""
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def iter_time_slices(
    since: datetime,
    until: datetime,
    *,
    slice_hours: float = 1.0,
) -> Iterator[tuple[datetime, datetime]]:
    """Yield half-open ``[start, end)`` windows covering ``[since, until)``."""
    if until <= since:
        return
    step = timedelta(hours=slice_hours)
    if step <= timedelta(0):
        raise ValueError("slice_hours must be positive")
    cursor = since
    while cursor < until:
        end = min(cursor + step, until)
        yield cursor, end
        cursor = end


def time_window_filter(since: datetime, until: datetime) -> str:
    """Build an MQL filter for ``meta.create_time`` in ``[since, until)``."""
    return (
        f"meta.create_time >= date({format_mql_date(since)}) and "
        f"meta.create_time < date({format_mql_date(until)})"
    )


__all__ = [
    "format_mql_date",
    "iter_time_slices",
    "parse_iso_utc",
    "time_window_filter",
]
