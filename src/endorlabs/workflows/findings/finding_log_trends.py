"""FindingLog CREATE/DELETE trend analysis for new-vs-resolved charts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from endorlabs.operations.group_by_time_wire import (
    GROUP_BY_TIME_INTERVAL_ALIASES,
    normalize_group_by_time_interval,
)
from endorlabs.tools.list_sharding import parallel_map_shards, project_scoped_filter
from endorlabs.workflows.findings.filters import (
    finding_log_time_window_filter,
    reachable_vuln_log_base_filter,
)
from endorlabs.workflows.logs.group_by_time import (
    group_by_time_counts,
    is_timeout_like,
)
from endorlabs.workflows.projects.inventory import discover_tenant_project_shards

if TYPE_CHECKING:
    from endorlabs import Client

FINDING_CRITERIA = (
    "Critical/High severity · reachable & potentially reachable · main context"
)

CHART_DEFAULT_INTERVAL = "week"
CHART_DEFAULT_LOOKBACK = 13
CHART_SUPPORTED_INTERVALS = frozenset({CHART_DEFAULT_INTERVAL})

# Keys required by ``generate_canvas.render_canvas`` (producer: ``build_analysis``).
CHART_ANALYSIS_CANVAS_KEYS: tuple[str, ...] = (
    "namespace",
    "categories",
    "cumulative_new",
    "cumulative_resolved",
    "finding_criteria",
    "period_caption",
    "gap_start",
    "gap_mid",
    "gap_end",
    "gap_mid_label",
    "gap_end_label",
    "gap_trend",
    "interval",
    "lookback",
)


def normalize_chart_interval(interval: str) -> str:
    """Validate and normalize a chart ``group_by_time`` interval alias."""
    cleaned = interval.strip().lower()
    if cleaned.startswith("group_by_time_interval_"):
        cleaned = cleaned.removeprefix("group_by_time_interval_")
    if cleaned not in GROUP_BY_TIME_INTERVAL_ALIASES:
        allowed = ", ".join(sorted(GROUP_BY_TIME_INTERVAL_ALIASES))
        msg = f"Unsupported interval {interval!r}; expected one of: {allowed}"
        raise ValueError(msg)
    if cleaned not in CHART_SUPPORTED_INTERVALS:
        supported = ", ".join(sorted(CHART_SUPPORTED_INTERVALS))
        msg = (
            f"Cumulative chart JSON supports interval in {{{supported}}}; "
            f"got {interval!r}"
        )
        raise ValueError(msg)
    return cleaned


def chart_window_params(data: dict[str, Any]) -> tuple[str, int]:
    """Resolve interval + lookback from analysis JSON (legacy lookback_days too)."""
    if "interval" in data and "lookback" in data:
        return normalize_chart_interval(str(data["interval"])), int(data["lookback"])
    if "lookback_days" in data:
        return CHART_DEFAULT_INTERVAL, max(1, round(int(data["lookback_days"]) / 7))
    msg = "chart analysis JSON needs interval+lookback (or legacy lookback_days)"
    raise ValueError(msg)


def validate_chart_analysis(data: dict[str, Any]) -> None:
    """Raise ``ValueError`` when *data* cannot be rendered as a cumulative chart."""
    required = list(CHART_ANALYSIS_CANVAS_KEYS)
    if "lookback_days" in data and "interval" not in data:
        required = [key for key in required if key not in ("interval", "lookback")]
    missing = [key for key in required if key not in data]
    if missing:
        msg = f"chart analysis JSON missing keys: {', '.join(missing)}"
        raise ValueError(msg)
    chart_window_params(data)

    week_count = len(data["categories"])
    if week_count == 0:
        raise ValueError("chart analysis has no week buckets")

    for series in ("cumulative_new", "cumulative_resolved"):
        if len(data[series]) != week_count:
            msg = (
                f"chart analysis length mismatch: categories={week_count} "
                f"{series}={len(data[series])}"
            )
            raise ValueError(msg)


def chart_canvas_filename(namespace: str, *, interval: str, lookback: int) -> str:
    """Return the canonical ``.canvas.tsx`` filename for a namespace and window."""
    slug = namespace.replace("_", "-")
    interval_slug = normalize_chart_interval(interval)
    return f"{slug}-cumulative-{interval_slug}-past-{lookback}.canvas.tsx"


def utc_sunday_start(dt: datetime) -> datetime:
    """Return UTC midnight at the start of the week containing *dt* (Sunday)."""
    dt = dt.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    days_since_sunday = (dt.weekday() + 1) % 7
    return dt - timedelta(days=days_since_sunday)


def compute_window(
    *,
    interval: str = CHART_DEFAULT_INTERVAL,
    lookback: int = CHART_DEFAULT_LOOKBACK,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Compute inclusive UTC window with complete *interval* buckets only."""
    interval = normalize_chart_interval(interval)
    if lookback < 1:
        raise ValueError("lookback must be >= 1")

    now = now or datetime.now(UTC)
    if interval == "week":
        window_end = utc_sunday_start(now)
        window_start = window_end - timedelta(weeks=lookback)
    else:
        msg = f"Window computation supports interval={CHART_DEFAULT_INTERVAL!r} only"
        raise ValueError(msg)

    if window_start >= window_end:
        raise ValueError("Computed window has no complete buckets")
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
    interval: str = CHART_DEFAULT_INTERVAL,
    lookback: int = CHART_DEFAULT_LOOKBACK,
) -> dict[str, Any]:
    """Build chart analysis JSON from weekly CREATE/DELETE bucket counts."""
    week_starts = iter_week_starts(window_start, window_end)
    if not week_starts:
        raise ValueError("window has no complete weeks for chart analysis")
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
        "interval": normalize_chart_interval(interval),
        "lookback": lookback,
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


def merge_count_dicts(dicts: list[dict[str, int]]) -> dict[str, int]:
    """Sum time-bucket counts from parallel shard queries."""
    merged: dict[str, int] = {}
    for counts in dicts:
        for bucket, count in counts.items():
            merged[bucket] = merged.get(bucket, 0) + count
    return merged


def _query_operation_group_counts(
    client: Client,
    *,
    namespace: str,
    base_filter: str,
    operation: str,
    level: str | None,
    traverse: bool,
    interval: str,
    project_uuid: str | None = None,
) -> dict[str, int]:
    filt = f"{base_filter} and spec.operation==OPERATION_{operation}"
    if level is not None:
        filt += f" and spec.level==FINDING_LEVEL_{level}"
    else:
        filt += " and spec.level in [FINDING_LEVEL_CRITICAL, FINDING_LEVEL_HIGH]"
    if project_uuid is not None:
        filt = project_scoped_filter(filt, project_uuid)

    return group_by_time_counts(
        client.FindingLog.list_groups,
        namespace=namespace,
        filter=filt,
        traverse=traverse,
        interval=interval,
    )


def _merge_severity_level_counts(
    client: Client,
    *,
    namespace: str,
    base_filter: str,
    operation: str,
    traverse: bool,
    interval: str,
) -> dict[str, int]:
    """Query CRITICAL and HIGH separately and merge bucket counts."""
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
    return merged


def _query_operation_counts_sharded(
    client: Client,
    *,
    namespace: str,
    base_filter: str,
    operation: str,
    interval: str,
    severity_split: bool,
    max_workers: int,
    max_project_pages: int | None,
) -> tuple[dict[str, int], bool]:
    """Per-project parallel fallback when aggregate ``group_by_time`` times out."""
    shards = discover_tenant_project_shards(
        client,
        namespace,
        max_pages=max_project_pages,
    )
    if not shards:
        return {}, severity_split

    def _shard_query(level: str | None) -> dict[str, int]:
        def worker(shard: Any) -> dict[str, int]:
            return _query_operation_group_counts(
                client,
                namespace=shard.namespace,
                base_filter=base_filter,
                operation=operation,
                level=level,
                traverse=False,
                interval=interval,
                project_uuid=shard.key,
            )

        results = parallel_map_shards(
            shards,
            worker,
            max_workers=max_workers,
            progress_label=f"FindingLog {operation} shards",
        )
        return merge_count_dicts(results)

    if not severity_split:
        try:
            return _shard_query(None), False
        except Exception as exc:
            if not is_timeout_like(exc):
                raise
            severity_split = True

    merged: dict[str, int] = {}
    for level in ("CRITICAL", "HIGH"):
        counts = _shard_query(level)
        for bucket, count in counts.items():
            merged[bucket] = merged.get(bucket, 0) + count
    return merged, True


def _query_operation_counts_aggregate(
    client: Client,
    *,
    namespace: str,
    base_filter: str,
    operation: str,
    interval: str,
    severity_split: bool,
) -> tuple[dict[str, int], bool]:
    """Single traverse ``group_by_time`` query (backend-indexed interval buckets)."""
    if not severity_split:
        try:
            counts = _query_operation_group_counts(
                client,
                namespace=namespace,
                base_filter=base_filter,
                operation=operation,
                level=None,
                traverse=True,
                interval=interval,
            )
            return counts, False
        except Exception as exc:
            if not is_timeout_like(exc):
                raise
            severity_split = True

    counts = _merge_severity_level_counts(
        client,
        namespace=namespace,
        base_filter=base_filter,
        operation=operation,
        traverse=True,
        interval=interval,
    )
    return counts, True


def query_operation_counts(
    client: Client,
    *,
    namespace: str,
    base_filter: str,
    operation: str,
    traverse: bool = True,
    severity_split: bool = False,
    interval: str = "week",
    max_workers: int = 12,
    max_project_pages: int | None = None,
) -> tuple[dict[str, int], bool]:
    """Return bucket counts and whether severity-split fallback was used.

    When ``traverse=True``, prefer one indexed ``group_by_time`` aggregate across
    the namespace tree; fall back to per-project parallel shards only on timeout.
    """
    if traverse:
        try:
            return _query_operation_counts_aggregate(
                client,
                namespace=namespace,
                base_filter=base_filter,
                operation=operation,
                interval=interval,
                severity_split=severity_split,
            )
        except Exception as exc:
            if not is_timeout_like(exc):
                raise
        return _query_operation_counts_sharded(
            client,
            namespace=namespace,
            base_filter=base_filter,
            operation=operation,
            interval=interval,
            severity_split=True,
            max_workers=max_workers,
            max_project_pages=max_project_pages,
        )

    if not severity_split:
        try:
            counts = _query_operation_group_counts(
                client,
                namespace=namespace,
                base_filter=base_filter,
                operation=operation,
                level=None,
                traverse=False,
                interval=interval,
            )
            return counts, False
        except Exception as exc:
            if not is_timeout_like(exc):
                raise
            severity_split = True

    counts = _merge_severity_level_counts(
        client,
        namespace=namespace,
        base_filter=base_filter,
        operation=operation,
        traverse=False,
        interval=interval,
    )
    return counts, True


def build_finding_log_new_vs_resolved_analysis(
    client: Client,
    namespace: str,
    *,
    interval: str = CHART_DEFAULT_INTERVAL,
    lookback: int = CHART_DEFAULT_LOOKBACK,
    traverse: bool = True,
    now: datetime | None = None,
    max_workers: int = 12,
    max_project_pages: int | None = None,
) -> dict[str, Any]:
    """Query FindingLog CREATE/DELETE counts and return new-vs-resolved chart JSON."""
    interval = normalize_chart_interval(interval)
    normalize_group_by_time_interval(interval)

    window_start, window_end = compute_window(
        interval=interval, lookback=lookback, now=now
    )
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
            max_workers=max_workers,
            max_project_pages=max_project_pages,
        )
        delete_counts, delete_split = query_operation_counts(
            client,
            namespace=namespace,
            base_filter=base_filter,
            operation="DELETE",
            traverse=traverse,
            severity_split=False,
            interval=interval,
            max_workers=max_workers,
            max_project_pages=max_project_pages,
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
            max_workers=max_workers,
            max_project_pages=max_project_pages,
        )
        delete_counts, _ = query_operation_counts(
            client,
            namespace=namespace,
            base_filter=base_filter,
            operation="DELETE",
            traverse=traverse,
            severity_split=True,
            interval=interval,
            max_workers=max_workers,
            max_project_pages=max_project_pages,
        )

    return build_analysis(
        namespace=namespace,
        window_start=window_start,
        window_end=window_end,
        create_counts=create_counts,
        delete_counts=delete_counts,
        severity_split=severity_split,
        interval=interval,
        lookback=lookback,
    )
