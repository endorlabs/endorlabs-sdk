#!/usr/bin/env python3
"""FindingLog weekly CREATE/DELETE analysis for cumulative new-vs-resolved charts."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

FINDING_CRITERIA = (
    "Critical/High severity · reachable & potentially reachable · main context"
)
BASE_SUFFIX = (
    "context.type==CONTEXT_TYPE_MAIN "
    "and spec.finding_categories contains FINDING_CATEGORY_VULNERABILITY "
    "and spec.finding_tags contains "
    "[FINDING_TAGS_REACHABLE_FUNCTION, FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION]"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Query FindingLog CREATE/DELETE weekly counts and write analysis JSON."
        )
    )
    parser.add_argument(
        "namespace",
        help="Tenant root or child namespace (--traverse includes children).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            ".endorlabs-context/workspace/sessions/agent/exports/new-vs-resolved"
        ),
        help="Directory for analysis JSON.",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=90,
        help="Rolling lookback in calendar days (default: 90).",
    )
    parser.add_argument(
        "--timeout",
        default="120s",
        help="endorctl per-query timeout (default: 120s).",
    )
    parser.add_argument(
        "--endorctl",
        default=None,
        help="Path to endorctl binary (default: PATH lookup).",
    )
    return parser.parse_args(argv)


def utc_sunday_start(dt: datetime) -> datetime:
    dt = dt.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    days_since_sunday = (dt.weekday() + 1) % 7
    return dt - timedelta(days=days_since_sunday)


def snap_forward_to_sunday(dt: datetime) -> datetime:
    dt = dt.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    if dt.weekday() == 6:
        return dt
    days_ahead = (6 - dt.weekday()) % 7
    return dt + timedelta(days=days_ahead)


def compute_window(
    now: datetime | None = None, lookback_days: int = 90
) -> tuple[datetime, datetime]:
    now = now or datetime.now(UTC)
    window_end = utc_sunday_start(now)
    lookback_start = window_end - timedelta(days=lookback_days)
    window_start = snap_forward_to_sunday(lookback_start)
    if window_start >= window_end:
        raise ValueError("Computed window has no complete weeks")
    return window_start, window_end


def iso_z(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def week_label(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%m/%d")


def iter_week_starts(window_start: datetime, window_end: datetime) -> list[datetime]:
    weeks: list[datetime] = []
    cursor = window_start
    while cursor < window_end:
        weeks.append(cursor)
        cursor += timedelta(days=7)
    return weeks


def parse_bucket_key(raw: str) -> str:
    cleaned = raw.strip().strip('"').strip("'")
    cleaned = cleaned.strip('"').strip("'")
    return cleaned


def extract_counts(payload: dict[str, Any]) -> dict[str, int]:
    groups = (payload.get("group_response") or {}).get("groups") or {}
    out: dict[str, int] = {}
    for key, value in groups.items():
        bucket = parse_bucket_key(str(key))
        count = int((value.get("aggregation_count") or {}).get("count") or 0)
        out[bucket] = out.get(bucket, 0) + count
    return out


def build_base_filter(window_start: datetime, window_end: datetime) -> str:
    return (
        f"meta.create_time>=date({iso_z(window_start)}) "
        f"and meta.create_time<date({iso_z(window_end)}) "
        f"and {BASE_SUFFIX}"
    )


def run_group_by_time(
    *,
    endorctl: str,
    namespace: str,
    base_filter: str,
    operation: str,
    level: str | None,
    timeout: str,
) -> dict[str, Any]:
    filt = f"{base_filter} and spec.operation==OPERATION_{operation}"
    if level is not None:
        filt += f" and spec.level==FINDING_LEVEL_{level}"
    else:
        filt += (
            " and spec.level in "
            "[FINDING_LEVEL_CRITICAL, FINDING_LEVEL_HIGH]"
        )

    cmd = [
        endorctl,
        "api",
        "list",
        "-r",
        "FindingLog",
        "-n",
        namespace,
        "--traverse",
        "-f",
        filt,
        "--group-by-time",
        "--group-aggregation-paths",
        "meta.create_time",
        "--group-by-time-interval",
        "week",
        "--group-by-time-mode",
        "count",
        f"--timeout={timeout}",
        "-o",
        "json",
        "--log-level",
        "error",
    ]
    env = os.environ.copy()
    if env.get("ENDOR_ADMIN_TOKEN") and not env.get("ENDOR_TOKEN"):
        env["ENDOR_TOKEN"] = env["ENDOR_ADMIN_TOKEN"]
    env.pop("ENDOR_API_CREDENTIALS_KEY", None)
    env.pop("ENDOR_API_CREDENTIALS_SECRET", None)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"endorctl failed ({operation}, level={level or 'CRITICAL+HIGH'}):\n"
            f"{result.stderr or result.stdout}"
        )
    return json.loads(result.stdout)


def query_operation_counts(
    *,
    endorctl: str,
    namespace: str,
    base_filter: str,
    operation: str,
    timeout: str,
    severity_split: bool,
) -> dict[str, int]:
    if not severity_split:
        try:
            payload = run_group_by_time(
                endorctl=endorctl,
                namespace=namespace,
                base_filter=base_filter,
                operation=operation,
                level=None,
                timeout=timeout,
            )
            return extract_counts(payload)
        except RuntimeError as exc:
            if "deadline" not in str(exc).lower() and "504" not in str(exc):
                raise
            severity_split = True

    merged: dict[str, int] = {}
    for level in ("CRITICAL", "HIGH"):
        payload = run_group_by_time(
            endorctl=endorctl,
            namespace=namespace,
            base_filter=base_filter,
            operation=operation,
            level=level,
            timeout=timeout,
        )
        for bucket, count in extract_counts(payload).items():
            merged[bucket] = merged.get(bucket, 0) + count
    return merged


def cumulative(values: list[int]) -> list[int]:
    total = 0
    out: list[int] = []
    for value in values:
        total += value
        out.append(total)
    return out


def gap_trend(gap_start: int, gap_end: int) -> str:
    if gap_end > gap_start:
        return "widening"
    if gap_end < gap_start:
        return "narrowing"
    return "stable"


def format_period_caption(window_start: datetime, last_week: datetime) -> str:
    end_inclusive = last_week + timedelta(days=6)
    return (
        f"{window_start.strftime('%b')} {window_start.day}, {window_start.year} – "
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


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    endorctl = args.endorctl or shutil.which("endorctl")
    if not endorctl:
        print("endorctl not found on PATH", file=sys.stderr)
        return 1

    window_start, window_end = compute_window(lookback_days=args.lookback_days)
    base_filter = build_base_filter(window_start, window_end)

    severity_split = False
    try:
        create_counts = query_operation_counts(
            endorctl=endorctl,
            namespace=args.namespace,
            base_filter=base_filter,
            operation="CREATE",
            timeout=args.timeout,
            severity_split=False,
        )
        delete_counts = query_operation_counts(
            endorctl=endorctl,
            namespace=args.namespace,
            base_filter=base_filter,
            operation="DELETE",
            timeout=args.timeout,
            severity_split=False,
        )
    except RuntimeError:
        severity_split = True
        create_counts = query_operation_counts(
            endorctl=endorctl,
            namespace=args.namespace,
            base_filter=base_filter,
            operation="CREATE",
            timeout=args.timeout,
            severity_split=True,
        )
        delete_counts = query_operation_counts(
            endorctl=endorctl,
            namespace=args.namespace,
            base_filter=base_filter,
            operation="DELETE",
            timeout=args.timeout,
            severity_split=True,
        )

    analysis = build_analysis(
        namespace=args.namespace,
        window_start=window_start,
        window_end=window_end,
        create_counts=create_counts,
        delete_counts=delete_counts,
        severity_split=severity_split,
    )

    slug = args.namespace.replace("_", "-")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{slug}-new-vs-resolved-analysis.json"
    out_path.write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    print(
        f"Weeks: {len(analysis['weeks'])} "
        f"({analysis['window_start']} .. {analysis['last_complete_week']}) "
        f"severity_split={analysis['severity_split']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
