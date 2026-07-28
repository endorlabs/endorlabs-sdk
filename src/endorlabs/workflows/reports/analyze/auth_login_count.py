#!/usr/bin/env python3
"""Aggregate AuthenticationLog login counts by identity and write CSV."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.context.paths import default_runs_dir, sanitize_path_segment
from endorlabs.workflows.auth import (
    LoginActivityRow,
    count_logins_from_groups,
    count_logins_from_rows,
    list_auth_logs,
)

RUN_BUCKET = "auth-login-count"


def _default_output_path(tenant: str, days: int) -> Path:
    safe_tenant = sanitize_path_segment(tenant)
    return default_runs_dir(RUN_BUCKET) / f"login-count-{safe_tenant}-{days}d.csv"


def _csv_fieldnames(days: int) -> list[str]:
    return [
        "identity",
        "user identifiers",
        "last login",
        f"login count in {days} days",
    ]


def write_login_count_csv(
    activity: list[LoginActivityRow],
    output: Path,
    *,
    days: int,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _csv_fieldnames(days)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in activity:
            writer.writerow(row.to_csv_row())


def build_summary(
    tenant: str,
    *,
    days: int,
    activity: list[LoginActivityRow],
    raw_row_count: int,
) -> dict[str, Any]:
    total_logins = sum(item.login_count for item in activity)
    top = [
        {
            "identity": item.identity,
            "login_count": item.login_count,
            "last_login": item.last_login,
        }
        for item in activity[:10]
    ]
    return {
        "tenant": tenant,
        "days": days,
        "identity_count": len(activity),
        "total_login_events": total_logins,
        "raw_rows_after_filters": raw_row_count,
        "top_identities": top,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report AuthenticationLog login counts by identity."
    )
    parser.add_argument(
        "--tenant",
        required=True,
        help="Tenant namespace hint for Client(tenant=...).",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Lookback window in days (default: 90).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV output path (default: workspace/runs/auth-login-count/...).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional cap on AuthenticationLog list pagination depth.",
    )
    parser.add_argument(
        "--include-failed",
        action="store_true",
        help="Include unsuccessful authentication events.",
    )
    parser.add_argument(
        "--include-api-key",
        action="store_true",
        help="Include API-key automation auth URIs.",
    )
    parser.add_argument(
        "--platform-wide",
        action="store_true",
        help=(
            "Use traverse=True when listing AuthenticationLog. Default scopes to "
            "the tenant list path only (-n <tenant>, traverse=False)."
        ),
    )
    parser.add_argument(
        "--list-rows",
        action="store_true",
        help="Aggregate client-side from full list rows instead of list_groups.",
    )
    parser.add_argument(
        "--json-summary",
        type=Path,
        default=None,
        help="Optional path for a JSON summary alongside the CSV.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.days < 1:
        print("error: --days must be >= 1", file=sys.stderr)
        return 2

    client = endorlabs.Client(tenant=args.tenant)
    output = args.output or _default_output_path(args.tenant, args.days)

    tenant_scoped = not args.platform_wide
    list_kwargs = {
        "days": args.days,
        "namespace": args.tenant,
        "traverse": not tenant_scoped,
        "max_pages": args.max_pages,
        "successful_only": not args.include_failed,
        "interactive_only": not args.include_api_key,
    }

    if args.list_rows:
        rows = list_auth_logs(
            client,
            exclude_api_key=not args.include_api_key,
            concurrent=False,
            **list_kwargs,
        )
        activity = count_logins_from_rows(rows, days=args.days)
        raw_row_count = len(rows)
    else:
        activity = count_logins_from_groups(client, **list_kwargs)
        raw_row_count = sum(item.login_count for item in activity)
    client.close()

    write_login_count_csv(activity, output, days=args.days)
    summary = build_summary(
        args.tenant,
        days=args.days,
        activity=activity,
        raw_row_count=raw_row_count,
    )

    if args.json_summary:
        args.json_summary.parent.mkdir(parents=True, exist_ok=True)
        summary_with_output = {**summary, "csv": str(output)}
        args.json_summary.write_text(
            json.dumps(summary_with_output, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    print(f"Wrote {output}")
    print(json.dumps(summary, indent=2, sort_keys=True))

    if activity:
        print("\nTop identities:")
        for item in activity[:10]:
            print(
                f"  {item.identity}: {item.login_count} logins (last {item.last_login})"
            )
    else:
        print("No login activity rows matched the filters.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
