"""FindingLog CREATE/DELETE trend analysis for new-vs-resolved charts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from endorlabs.workflows.findings.filters import (
    finding_log_time_window_filter,
    reachable_vuln_log_base_filter,
)
from endorlabs.workflows.logs.group_by_time import (
    group_by_time_counts,
    is_timeout_like,
)

if TYPE_CHECKING:
    from endorlabs import Client

FINDING_CRITERIA = (
    "Critical/High severity · reachable & potentially reachable · main context"
)


def utc_sunday_start(dt: datetime) -> datetime:
    """Return UTC midnight at the start of the week containing *dt* (Sunday)."""
    dt = dt.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    days_since_sunday = (dt.weekday() + 1) % 7
    return dt - timedelta(days=days_since_sunday)


def snap_forward_to_sunday(dt: datetime) -> datetime:
    """Snap *dt* forward to UTC Sunday midnight (inclusive if already Sunday)."""
    dt = dt.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    if dt.weekday() == 6:
        return dt
    days_ahead = (6 - dt.weekday()) % 7
    return dt + timedelta(days=days_ahead)


def compute_window(
    now: datetime | None = None, lookback_days: int = 90
) -> tuple[datetime, datetime]:
    """Compute inclusive UTC week window with complete weeks only."""
    now = now or datetime.now(UTC)
    window_end = utc_sunday_start(now)
    lookback_start = window_end - timedelta(days=lookback_days)
    window_start = snap_forward_to_sunday(lookback_start)
    if window_start >= window_end:
        raise ValueError("Computed window has no complete weeks")
    return window_start, window_end


def iso_z(dt: datetime) -> str:
    """Format *dt* as ISO-8601 UTC with ``Z`` suffix."""
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def week_label(dt: datetime) -> str:
    """Return ``MM/DD`` chart label for a week start."""
    return dt.astimezone(UTC).strftime("%m/%d")


def iter_week_starts(window_start: datetime, window_end: datetime) -> list[datetime]:
    """Yield UTC Sunday midnights from *window_start* until *window_end*."""
    weeks: list[datetime] = []
    cursor = window_start
    while cursor < window_end:
        weeks.append(cursor)
        cursor += timedelta(days=7)
    return weeks


def build_base_filter(window_start: datetime, window_end: datetime) -> str:
    """Build FindingLog list filter for the chart time window and tag set."""
    return finding_log_time_window_filter(
        window_start,
        window_end,
        base_filter=reachable_vuln_log_base_filter(),
    )


def cumulative(values: list[int]) -> list[int]:
    """Return running totals for *values*."""
    total = 0
    out: list[int] = []
    for value in values:
        total += value
        out.append(total)
    return out


def gap_trend(gap_start: int, gap_end: int) -> str:
    """Classify cumulative gap movement as widening, narrowing, or stable."""
    if gap_end > gap_start:
        return "widening"
    if gap_end < gap_start:
        return "narrowing"
    return "stable"


def format_period_caption(window_start: datetime, last_week: datetime) -> str:
    """Human-readable inclusive date range for chart captions."""
    end_inclusive = last_week + timedelta(days=6)
    return (
        f"{window_start.strftime('%b')} {window_start.day}, {window_start.year} – "  # noqa: RUF001
        f"{end_inclusive.strftime('%b')} {end_inclusive.day}, {end_inclusive.year}"
    )


def build_analysis(
    *,
    namespace: str,
    window_start: datetime,
    window_end: datetime,
    create_counts: dict[str, int],
    delete_counts: dict[str, int],
    severity_split: bool,
) -> dict[str, Any]:
    """Build chart analysis JSON from weekly CREATE/DELETE bucket counts."""
    week_starts = iter_week_starts(window_start, window_end)
    weeks: list[dict[str, Any]] = []
    weekly_new: list[int] = []
    weekly_resolved: list[int] = []

    for week in week_starts:
        key = iso_z(week)
        new_count = int(create_counts.get(key, 0))
        resolved_count = int(delete_counts.get(key, 0))
        weekly_new.append(new_count)
        weekly_resolved.append(resolved_count)
        weeks.append(
            {
                "week_start": key,
                "label": week_label(week),
                "weekly_new": new_count,
                "weekly_resolved": resolved_count,
            }
        )

    cumulative_new = cumulative(weekly_new)
    cumulative_resolved = cumulative(weekly_resolved)
    gaps = [n - r for n, r in zip(cumulative_new, cumulative_resolved, strict=True)]

    for idx, week in enumerate(weeks):
        week["cumulative_new"] = cumulative_new[idx]
        week["cumulative_resolved"] = cumulative_resolved[idx]
        week["gap"] = gaps[idx]

    last_week = week_starts[-1]
    mid_idx = len(week_starts) // 2

    return {
        "namespace": namespace,
        "window_start": iso_z(window_start),
        "window_end": iso_z(window_end),
        "last_complete_week": iso_z(last_week),
        "lookback_days": (window_end - window_start).days,
        "context_type": "CONTEXT_TYPE_MAIN",
        "finding_criteria": FINDING_CRITERIA,
        "severity_split": severity_split,
        "weeks": weeks,
        "categories": [week["label"] for week in weeks],
        "weekly_new": weekly_new,
        "weekly_resolved": weekly_resolved,
        "cumulative_new": cumulative_new,
        "cumulative_resolved": cumulative_resolved,
        "gaps": gaps,
        "gap_start": gaps[0] if gaps else 0,
        "gap_mid": gaps[mid_idx] if gaps else 0,
        "gap_end": gaps[-1] if gaps else 0,
        "gap_mid_label": weeks[mid_idx]["label"] if weeks else "",
        "gap_end_label": weeks[-1]["label"] if weeks else "",
        "gap_trend": gap_trend(gaps[0], gaps[-1]) if gaps else "stable",
        "period_caption": format_period_caption(window_start, last_week),
        "generated_at": iso_z(datetime.now(UTC)),
    }


def _query_operation_group_counts(
    client: Client,
    *,
    namespace: str,
    base_filter: str,
    operation: str,
    level: str | None,
    traverse: bool,
    interval: str,
) -> dict[str, int]:
    filt = f"{base_filter} and spec.operation==OPERATION_{operation}"
    if level is not None:
        filt += f" and spec.level==FINDING_LEVEL_{level}"
    else:
        filt += " and spec.level in [FINDING_LEVEL_CRITICAL, FINDING_LEVEL_HIGH]"

    return group_by_time_counts(
        client.FindingLog.list_groups,
        namespace=namespace,
        filter=filt,
        traverse=traverse,
        interval=interval,
    )


def query_operation_counts(
    client: Client,
    *,
    namespace: str,
    base_filter: str,
    operation: str,
    traverse: bool = True,
    severity_split: bool = False,
    interval: str = "week",
) -> tuple[dict[str, int], bool]:
    """Return bucket counts and whether severity-split fallback was used."""
    if not severity_split:
        try:
            counts = _query_operation_group_counts(
                client,
                namespace=namespace,
                base_filter=base_filter,
                operation=operation,
                level=None,
                traverse=traverse,
                interval=interval,
            )
            return counts, False
        except Exception as exc:
            if not is_timeout_like(exc):
                raise
            severity_split = True

    merged: dict[str, int] = {}
    for level in ("CRITICAL", "HIGH"):
        counts = _query_operation_group_counts(
            client,
            namespace=namespace,
            base_filter=base_filter,
            operation=operation,
            level=level,
            traverse=traverse,
            interval=interval,
        )
        for bucket, count in counts.items():
            merged[bucket] = merged.get(bucket, 0) + count
    return merged, True


def build_finding_log_new_vs_resolved_analysis(
    client: Client,
    namespace: str,
    *,
    lookback_days: int = 90,
    traverse: bool = True,
    now: datetime | None = None,
    interval: str = "week",
) -> dict[str, Any]:
    """Query FindingLog CREATE/DELETE counts and return new-vs-resolved chart JSON."""
    if interval != "week":
        msg = (
            "Only interval='week' is supported for cumulative new-vs-resolved "
            "chart JSON; use group_by_time_counts for other intervals."
        )
        raise ValueError(msg)

    window_start, window_end = compute_window(now=now, lookback_days=lookback_days)
    base_filter = build_base_filter(window_start, window_end)

    severity_split = False
    try:
        create_counts, create_split = query_operation_counts(
            client,
            namespace=namespace,
            base_filter=base_filter,
            operation="CREATE",
            traverse=traverse,
            severity_split=False,
            interval=interval,
        )
        delete_counts, delete_split = query_operation_counts(
            client,
            namespace=namespace,
            base_filter=base_filter,
            operation="DELETE",
            traverse=traverse,
            severity_split=False,
            interval=interval,
        )
        severity_split = create_split or delete_split
    except Exception as exc:
        if not is_timeout_like(exc):
            raise
        severity_split = True
        create_counts, _ = query_operation_counts(
            client,
            namespace=namespace,
            base_filter=base_filter,
            operation="CREATE",
            traverse=traverse,
            severity_split=True,
            interval=interval,
        )
        delete_counts, _ = query_operation_counts(
            client,
            namespace=namespace,
            base_filter=base_filter,
            operation="DELETE",
            traverse=traverse,
            severity_split=True,
            interval=interval,
        )

    return build_analysis(
        namespace=namespace,
        window_start=window_start,
        window_end=window_end,
        create_counts=create_counts,
        delete_counts=delete_counts,
        severity_split=severity_split,
    )


def build_weekly_finding_log_analysis(
    client: Client,
    namespace: str,
    *,
    lookback_days: int = 90,
    traverse: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Deprecated alias for :func:`build_finding_log_new_vs_resolved_analysis`."""
    return build_finding_log_new_vs_resolved_analysis(
        client,
        namespace,
        lookback_days=lookback_days,
        traverse=traverse,
        now=now,
        interval="week",
    )
