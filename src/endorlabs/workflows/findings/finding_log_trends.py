"""FindingLog CREATE/DELETE trend analysis for new-vs-resolved charts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from endorlabs.filters import (
    finding_log_time_window_filter,
    reachable_vuln_log_base_filter,
)
from endorlabs.operations.group_by_time_wire import (
    GROUP_BY_TIME_INTERVAL_ALIASES,
    normalize_group_by_time_interval,
)
from endorlabs.tools.list_sharding import parallel_map_shards
from endorlabs.workflows.logs.group_by_time import (
    group_by_time_counts,
    is_timeout_like,
)

if TYPE_CHECKING:
    from endorlabs import Client

FINDING_CRITERIA = (
    "All severities (Critical-Low) · main context · function-reach selections "
    "(default any reachability; also RF+PRF / RF / PRF / unreachable function); "
    "UI severity thresholds (Critical+ / High+ / Medium+ / All)"
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


# Severity x reachability cells for executive / multi-series FindingLog pulls.
REACHABLE_FUNCTION_CLAUSE = "spec.finding_tags contains FINDING_TAGS_REACHABLE_FUNCTION"
PRF_FUNCTION_CLAUSE = (
    "spec.finding_tags contains FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION"
)
UNREACHABLE_FUNCTION_CLAUSE = (
    "spec.finding_tags contains FINDING_TAGS_UNREACHABLE_FUNCTION"
)
# Base pull cells (Crit/High/Med/Low x each). ``any`` is unfiltered (no reach
# tag clause). ``all`` (RF+PRF) is derived in ``expand_severity_reach_matrix``.
# Dependency-axis tags (RD/PRD/UD) are omitted: function reach implies a
# reachable dependency in the product model, so RD-only options duplicate the
# function facet for prioritization and inflate FindingLog pull cost.
BASE_REACH_KEYS: tuple[str, ...] = (
    "any",
    "reachable",
    "prf",
    "unreachable_function",
)
EXACT_SEVERITY_LEVELS: tuple[tuple[str, str], ...] = (
    ("critical", "CRITICAL"),
    ("high", "HIGH"),
    ("medium", "MEDIUM"),
    ("low", "LOW"),
)
UNSPLIT_SEVERITY_LEVELS: tuple[str, ...] = tuple(
    level for _, level in EXACT_SEVERITY_LEVELS
)
_REACH_CLAUSES: tuple[tuple[str, str], ...] = (
    ("any", ""),
    ("reachable", REACHABLE_FUNCTION_CLAUSE),
    ("prf", PRF_FUNCTION_CLAUSE),
    ("unreachable_function", UNREACHABLE_FUNCTION_CLAUSE),
)
SEVERITY_REACH_CELLS: tuple[tuple[str, str, str, str], ...] = tuple(
    (sev, reach, level, clause)
    for sev, level in EXACT_SEVERITY_LEVELS
    for reach, clause in _REACH_CLAUSES
)


def append_parent_uuid_filter(
    base_filter: str,
    parent_uuids: list[str] | None,
) -> str:
    """Scope a FindingLog filter to ``meta.parent_uuid`` (project UUID set).

    ``None`` leaves the filter unchanged (whole namespace). An empty list forces
    a no-match sentinel so callers can represent an empty project set.
    """
    if parent_uuids is None:
        return base_filter
    if not parent_uuids:
        return f'{base_filter} and meta.parent_uuid=="__none__"'
    inner = ", ".join(f'"{u}"' for u in parent_uuids)
    return f"{base_filter} and meta.parent_uuid in [{inner}]"


def series_cell_from_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Map ``build_analysis`` output to a compact series cell (camelCase keys)."""
    return {
        "categories": analysis["categories"],
        "weeklyNew": analysis["weekly_new"],
        "weeklyResolved": analysis["weekly_resolved"],
        "cumulativeNew": analysis["cumulative_new"],
        "cumulativeResolved": analysis["cumulative_resolved"],
        "gaps": analysis["gaps"],
        "gapStart": analysis["gap_start"],
        "gapEnd": analysis["gap_end"],
        "gapTrend": analysis["gap_trend"],
        "periodCaption": analysis["period_caption"],
    }


def empty_series_cell(
    categories: list[str],
    period_caption: str,
) -> dict[str, Any]:
    """Zero-filled series cell matching *categories* length."""
    z = [0] * len(categories)
    return {
        "categories": categories,
        "weeklyNew": list(z),
        "weeklyResolved": list(z),
        "cumulativeNew": list(z),
        "cumulativeResolved": list(z),
        "gaps": list(z),
        "gapStart": 0,
        "gapEnd": 0,
        "gapTrend": "stable",
        "periodCaption": period_caption,
    }


def sum_series_cells(
    parts: list[dict[str, Any]],
    *,
    categories: list[str],
    period_caption: str,
) -> dict[str, Any]:
    """Sum weekly new/resolved across cells and recompute cumulative gap series."""
    if not parts:
        return empty_series_cell(categories, period_caption)
    n = len(categories)
    weekly_new = [0] * n
    weekly_resolved = [0] * n
    for part in parts:
        for i in range(n):
            weekly_new[i] += int(part["weeklyNew"][i])
            weekly_resolved[i] += int(part["weeklyResolved"][i])
    cum_new: list[int] = []
    cum_res: list[int] = []
    rn = rr = 0
    for a, b in zip(weekly_new, weekly_resolved, strict=True):
        rn += a
        rr += b
        cum_new.append(rn)
        cum_res.append(rr)
    gaps = [a - b for a, b in zip(cum_new, cum_res, strict=True)]
    gap_start = gaps[0] if gaps else 0
    gap_end = gaps[-1] if gaps else 0
    return {
        "categories": categories,
        "weeklyNew": weekly_new,
        "weeklyResolved": weekly_resolved,
        "cumulativeNew": cum_new,
        "cumulativeResolved": cum_res,
        "gaps": gaps,
        "gapStart": gap_start,
        "gapEnd": gap_end,
        "gapTrend": gap_trend(gap_start, gap_end),
        "periodCaption": period_caption,
    }


def expand_severity_reach_matrix(
    matrix: dict[str, dict[str, dict[str, Any]]],
    *,
    categories: list[str],
    period_caption: str,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Fill severity/reach rollups from Crit/High/Med/Low x function-reach cells.

    Per-severity ``any`` is the unfiltered FindingLog pull (no reach tag).
    ``all`` is the RF+PRF union (function-level actionable). Dependency-axis
    facets are not modeled here (RF implies RD in the product model).
    Top-level ``all`` severity sums all four exact severity rows. Missing base
    cells become zeros.
    """

    def combine(parts: list[dict[str, Any]]) -> dict[str, Any]:
        return sum_series_cells(
            parts, categories=categories, period_caption=period_caption
        )

    def cell(sev: str, reach: str) -> dict[str, Any]:
        row = matrix.get(sev) or {}
        found = row.get(reach)
        if isinstance(found, dict):
            return found
        return empty_series_cell(categories, period_caption)

    def sev_row(sev: str) -> dict[str, dict[str, Any]]:
        any_reach = cell(sev, "any")
        reachable = cell(sev, "reachable")
        prf = cell(sev, "prf")
        uf = cell(sev, "unreachable_function")
        return {
            "any": any_reach,
            "all": combine([reachable, prf]),
            "reachable": reachable,
            "prf": prf,
            "unreachable_function": uf,
        }

    exact = {sev: sev_row(sev) for sev, _level in EXACT_SEVERITY_LEVELS}
    reach_keys = (
        "any",
        "all",
        "reachable",
        "prf",
        "unreachable_function",
    )
    return {
        "all": {
            reach: combine([exact[sev][reach] for sev, _ in EXACT_SEVERITY_LEVELS])
            for reach in reach_keys
        },
        **exact,
    }


def query_operation_group_counts(
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
    """Run one FindingLog ``group_by_time`` count for CREATE or DELETE."""
    filt = f"{base_filter} and spec.operation==OPERATION_{operation}"
    if level is not None:
        filt += f" and spec.level==FINDING_LEVEL_{level}"
    else:
        inner = ", ".join(f"FINDING_LEVEL_{item}" for item in UNSPLIT_SEVERITY_LEVELS)
        filt += f" and spec.level in [{inner}]"
    if project_uuid is not None:
        # FindingLog is scoped by meta.parent_uuid (spec.project_uuid is 400).
        filt = f'{filt} and meta.parent_uuid=="{project_uuid}"'

    return group_by_time_counts(
        client.FindingLog.list_groups,
        namespace=namespace,
        filter=filt,
        traverse=traverse,
        interval=interval,
    )


# Compat alias for older call sites / tests that imported the private name.
_query_operation_group_counts = query_operation_group_counts


def _shards_for_parent_scope(
    client: Client,
    namespace: str,
    parent_uuids: list[str] | None,
    *,
    max_project_pages: int | None,
) -> list[Any]:
    """Project shards for leaf/tenant FindingLog escalate (timeout fallback)."""
    from endorlabs.tools.list_sharding import ProjectShard

    if parent_uuids is not None:
        return [
            ProjectShard(project_uuid=str(uid), namespace=namespace)
            for uid in parent_uuids
            if uid
        ]
    return list(
        client.Query.Project.discover(
            namespace,
            traverse=True,
            max_pages=max_project_pages,
        ).project_shards()
    )


def query_operation_group_counts_resilient(
    client: Client,
    *,
    namespace: str,
    base_filter: str,
    operation: str,
    level: str | None,
    interval: str,
    parent_uuids: list[str] | None = None,
    max_workers: int = 12,
    max_project_pages: int | None = None,
) -> dict[str, int]:
    """``group_by_time`` with timeout→per-project shard escalate (chart pattern).

    Tries one aggregate for the namespace (optional ``parent_uuids`` is_in). On
    timeout-like errors with multi-project scope, fans out via
    :func:`parallel_map_shards`. Single-project scope does not escalate.
    """
    if parent_uuids is not None and len(parent_uuids) == 0:
        return {}

    single_uuid = (
        parent_uuids[0] if parent_uuids is not None and len(parent_uuids) == 1 else None
    )
    try:
        if single_uuid is not None:
            return query_operation_group_counts(
                client,
                namespace=namespace,
                base_filter=base_filter,
                operation=operation,
                level=level,
                traverse=False,
                interval=interval,
                project_uuid=single_uuid,
            )
        scoped = append_parent_uuid_filter(base_filter, parent_uuids)
        return query_operation_group_counts(
            client,
            namespace=namespace,
            base_filter=scoped,
            operation=operation,
            level=level,
            traverse=False,
            interval=interval,
        )
    except Exception as exc:
        if single_uuid is not None or not is_timeout_like(exc):
            raise

    shards = _shards_for_parent_scope(
        client,
        namespace,
        parent_uuids,
        max_project_pages=max_project_pages,
    )
    if not shards:
        return {}

    def worker(shard: Any) -> dict[str, int]:
        try:
            return query_operation_group_counts(
                client,
                namespace=shard.namespace,
                base_filter=base_filter,
                operation=operation,
                level=level,
                traverse=False,
                interval=interval,
                project_uuid=shard.project_uuid,
            )
        except Exception as exc:
            if is_timeout_like(exc):
                return {}
            raise

    results = parallel_map_shards(
        shards,
        worker,
        max_workers=max(1, max_workers),
        progress_label=f"FindingLog {operation} shards",
    )
    return merge_count_dicts(results)


def query_severity_facet_series_cell(
    client: Client,
    *,
    namespace: str,
    window_start: datetime,
    window_end: datetime,
    category_base_filter: str,
    facet_clause: str,
    level: str,
    parent_uuids: list[str] | None = None,
    lookback: int = CHART_DEFAULT_LOOKBACK,
    interval: str = CHART_DEFAULT_INTERVAL,
    max_workers: int = 12,
    max_project_pages: int | None = None,
) -> dict[str, Any]:
    """Query one severity x facet FindingLog CREATE/DELETE series cell.

    *facet_clause* may be empty (category-only / ``all`` facet). *parent_uuids*
    scopes to ``meta.parent_uuid``; ``None`` means the whole namespace path.

    Multi-project / leaf aggregates escalate to project shards on timeout
    (same ladder as :func:`query_operation_counts`).
    """
    clause = category_base_filter
    extra = (facet_clause or "").strip()
    if extra:
        clause = f"{clause} and {extra}"
    base = finding_log_time_window_filter(
        window_start,
        window_end,
        base_filter=clause,
    )
    create = query_operation_group_counts_resilient(
        client,
        namespace=namespace,
        base_filter=base,
        operation="CREATE",
        level=level,
        interval=interval,
        parent_uuids=parent_uuids,
        max_workers=max_workers,
        max_project_pages=max_project_pages,
    )
    delete = query_operation_group_counts_resilient(
        client,
        namespace=namespace,
        base_filter=base,
        operation="DELETE",
        level=level,
        interval=interval,
        parent_uuids=parent_uuids,
        max_workers=max_workers,
        max_project_pages=max_project_pages,
    )
    return series_cell_from_analysis(
        build_analysis(
            namespace=namespace,
            window_start=window_start,
            window_end=window_end,
            create_counts=create,
            delete_counts=delete,
            severity_split=True,
            interval=interval,
            lookback=lookback,
        )
    )


def expand_severity_facet_matrix(
    matrix: dict[str, dict[str, dict[str, Any]]],
    *,
    facet_keys: tuple[str, ...] | list[str],
    categories: list[str],
    period_caption: str,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Fill severity ``all`` rollups from Crit/High/Med/Low x facet base cells."""

    def combine(parts: list[dict[str, Any]]) -> dict[str, Any]:
        return sum_series_cells(
            parts, categories=categories, period_caption=period_caption
        )

    def cell(sev: str, facet: str) -> dict[str, Any]:
        row = matrix.get(sev) or {}
        found = row.get(facet)
        if isinstance(found, dict):
            return found
        return empty_series_cell(categories, period_caption)

    exact = {
        sev: {facet: cell(sev, facet) for facet in facet_keys}
        for sev, _level in EXACT_SEVERITY_LEVELS
    }
    return {
        "all": {
            facet: combine([exact[sev][facet] for sev, _ in EXACT_SEVERITY_LEVELS])
            for facet in facet_keys
        },
        **exact,
    }


def query_severity_facet_matrix(
    client: Client,
    *,
    namespace: str,
    window_start: datetime,
    window_end: datetime,
    category_base_filter: str,
    cells: tuple[tuple[str, str, str, str], ...],
    facet_keys: tuple[str, ...] | list[str],
    parent_uuids: list[str] | None = None,
    lookback: int = CHART_DEFAULT_LOOKBACK,
    categories: list[str] | None = None,
    period_caption: str | None = None,
    interval: str = CHART_DEFAULT_INTERVAL,
    expand: str = "severity",
    max_workers: int = 12,
    max_project_pages: int | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Query severity x facet cells and expand rollups.

    *cells* rows are ``(severity, facet, level, facet_clause)``. Failed cells
    become zeros so callers can still roll up partial results.

    *expand*:
    - ``"severity"`` — sum Crit+High+Med+Low per facet (SAST / Secrets / AI-SAST).
    - ``"reach"`` — SCA function-reach rollups (``any`` = unfiltered; ``all`` =
      RF+PRF). *facet_keys* is unused for the expand step.
    """
    if categories is None or period_caption is None:
        _seed_sev, _seed_facet, seed_level, seed_clause = cells[0]
        seed = query_severity_facet_series_cell(
            client,
            namespace=namespace,
            window_start=window_start,
            window_end=window_end,
            category_base_filter=category_base_filter,
            facet_clause=seed_clause,
            level=seed_level,
            parent_uuids=parent_uuids,
            lookback=lookback,
            interval=interval,
            max_workers=max_workers,
            max_project_pages=max_project_pages,
        )
        categories = list(seed["categories"])
        period_caption = str(seed["periodCaption"])

    matrix: dict[str, dict[str, dict[str, Any]]] = {}
    for sev, facet, level, clause in cells:
        matrix.setdefault(sev, {})
        try:
            matrix[sev][facet] = query_severity_facet_series_cell(
                client,
                namespace=namespace,
                window_start=window_start,
                window_end=window_end,
                category_base_filter=category_base_filter,
                facet_clause=clause,
                level=level,
                parent_uuids=parent_uuids,
                lookback=lookback,
                interval=interval,
                max_workers=max_workers,
                max_project_pages=max_project_pages,
            )
        except Exception:
            matrix[sev][facet] = empty_series_cell(categories, period_caption)
    if expand == "reach":
        return expand_severity_reach_matrix(
            matrix, categories=categories, period_caption=period_caption
        )
    if expand != "severity":
        msg = f"Unsupported expand mode {expand!r}; expected 'severity' or 'reach'"
        raise ValueError(msg)
    return expand_severity_facet_matrix(
        matrix,
        facet_keys=facet_keys,
        categories=categories,
        period_caption=period_caption,
    )


def query_severity_reach_series_cell(
    client: Client,
    *,
    namespace: str,
    window_start: datetime,
    window_end: datetime,
    reach_clause: str,
    level: str,
    parent_uuids: list[str] | None = None,
    lookback: int = CHART_DEFAULT_LOOKBACK,
    interval: str = CHART_DEFAULT_INTERVAL,
) -> dict[str, Any]:
    """Query one severity x reach FindingLog CREATE/DELETE series cell.

    *parent_uuids* scopes to ``meta.parent_uuid`` (project UUID set). Pass
    ``None`` for the whole namespace path.
    """
    from endorlabs.filters import main_context_vulnerability_filter

    return query_severity_facet_series_cell(
        client,
        namespace=namespace,
        window_start=window_start,
        window_end=window_end,
        category_base_filter=main_context_vulnerability_filter(),
        facet_clause=reach_clause,
        level=level,
        parent_uuids=parent_uuids,
        lookback=lookback,
        interval=interval,
    )


def query_severity_reach_matrix(
    client: Client,
    *,
    namespace: str,
    window_start: datetime,
    window_end: datetime,
    parent_uuids: list[str] | None = None,
    lookback: int = CHART_DEFAULT_LOOKBACK,
    categories: list[str] | None = None,
    period_caption: str | None = None,
    interval: str = CHART_DEFAULT_INTERVAL,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Query Crit/High x base reach cells and expand severity/reach rollups.

    Thin wrapper over :func:`query_severity_facet_matrix` with ``expand="reach"``.
    """
    from endorlabs.filters import main_context_vulnerability_filter

    return query_severity_facet_matrix(
        client,
        namespace=namespace,
        window_start=window_start,
        window_end=window_end,
        category_base_filter=main_context_vulnerability_filter(),
        cells=SEVERITY_REACH_CELLS,
        facet_keys=BASE_REACH_KEYS,
        parent_uuids=parent_uuids,
        lookback=lookback,
        categories=categories,
        period_caption=period_caption,
        interval=interval,
        expand="reach",
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
    """Query each unsplit severity separately and merge bucket counts."""
    merged: dict[str, int] = {}
    for level in UNSPLIT_SEVERITY_LEVELS:
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
    shards = client.Query.Project.discover(
        namespace,
        traverse=True,
        max_pages=max_project_pages,
    ).project_shards()
    if not shards:
        return {}, severity_split

    def _shard_query(level: str | None) -> dict[str, int]:
        def worker(shard: Any) -> dict[str, int]:
            try:
                return _query_operation_group_counts(
                    client,
                    namespace=shard.namespace,
                    base_filter=base_filter,
                    operation=operation,
                    level=level,
                    traverse=False,
                    interval=interval,
                    project_uuid=shard.project_uuid,
                )
            except Exception as exc:
                if is_timeout_like(exc):
                    return {}
                raise

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
    for level in UNSPLIT_SEVERITY_LEVELS:
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
