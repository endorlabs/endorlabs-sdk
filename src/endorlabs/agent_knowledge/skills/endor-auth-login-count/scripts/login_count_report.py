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
from endorlabs.context.paths import workflow_sessions_root
from endorlabs.workflows.auth import (
    LoginActivityRow,
    aggregate_login_activity,
    aggregate_login_activity_from_groups,
    fetch_authentication_logs,
)


def _default_output_path(tenant: str, days: int, user_slug: str) -> Path:
    safe_tenant = tenant.replace("/", "-")
    return (
        workflow_sessions_root()
        / user_slug
        / "exports"
        / f"login-count-{safe_tenant}-{days}d.csv"
    )


def _resolve_user_slug(client: endorlabs.Client) -> str:
    try:
        whoami = client.whoami()
    except Exception:
        return "agent"
    email = str(getattr(whoami, "email", "") or "")
    if email and "@" in email:
        local = email.split("@", 1)[0]
        return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in local)
    return "agent"


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
        help="CSV output path (default: workspace/sessions/<user>/exports/...).",
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
    user_slug = _resolve_user_slug(client)
    output = args.output or _default_output_path(args.tenant, args.days, user_slug)

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
        rows = fetch_authentication_logs(
            client,
            exclude_api_key=not args.include_api_key,
            concurrent=False,
            **list_kwargs,
        )
        activity = aggregate_login_activity(rows, days=args.days)
        raw_row_count = len(rows)
    else:
        activity = aggregate_login_activity_from_groups(client, **list_kwargs)
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
