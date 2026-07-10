#!/usr/bin/env python3
"""Audit APIKey expiration across a tenant namespace path and write CSV."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.context.paths import default_runs_dir, sanitize_path_segment
from endorlabs.workflows.auth.credential_expiry import (
    CredentialExpiryRow,
    audit_api_key_expiry,
)

RUN_BUCKET = "auth-credential-expiry"


def _default_output_path(tenant: str, within_days: int) -> Path:
    safe_tenant = sanitize_path_segment(tenant)
    return (
        default_runs_dir(RUN_BUCKET)
        / f"credential-expiry-{safe_tenant}-{within_days}d.csv"
    )


def _csv_fieldnames() -> list[str]:
    return [
        "kind",
        "name",
        "namespace",
        "uuid",
        "key id",
        "expiration time",
        "status",
        "days until expiry",
        "propagate",
        "issuing user",
    ]


def write_credential_expiry_csv(
    rows: list[CredentialExpiryRow],
    output: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _csv_fieldnames()
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())


def build_summary(
    tenant: str,
    *,
    within_days: int,
    rows: list[CredentialExpiryRow],
    raw_row_count: int,
) -> dict[str, Any]:
    expired = sum(1 for row in rows if row.status == "expired")
    expiring = sum(1 for row in rows if row.status == "expiring_soon")
    unknown = sum(1 for row in rows if row.status == "unknown")
    return {
        "tenant": tenant,
        "within_days": within_days,
        "reported_rows": len(rows),
        "raw_api_keys_listed": raw_row_count,
        "expired_count": expired,
        "expiring_soon_count": expiring,
        "unknown_expiration_count": unknown,
        "top_rows": [
            {
                "name": row.name,
                "namespace": row.namespace,
                "status": row.status,
                "expiration_time": row.expiration_time,
                "days_until_expiry": row.days_until_expiry,
            }
            for row in rows[:10]
        ],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report expired or soon-to-expire API keys for a tenant."
    )
    parser.add_argument(
        "--tenant",
        required=True,
        help="Tenant namespace hint for Client(tenant=...) and list namespace=.",
    )
    parser.add_argument(
        "--within-days",
        type=int,
        default=30,
        help="Flag keys expiring within this many days (default: 30).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV output path (default: workspace/runs/auth-credential-expiry/...).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional cap on APIKey list pagination depth.",
    )
    parser.add_argument(
        "--platform-wide",
        action="store_true",
        help=(
            "Use traverse=True when listing APIKey. Default scopes to the tenant "
            "list path only (-n <tenant>, traverse=False)."
        ),
    )
    parser.add_argument(
        "--include-healthy",
        action="store_true",
        help="Include API keys that are not expired or expiring soon.",
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
    if args.within_days < 0:
        print("error: --within-days must be >= 0", file=sys.stderr)
        return 2

    client = endorlabs.Client(tenant=args.tenant)
    output = args.output or _default_output_path(args.tenant, args.within_days)

    all_rows = audit_api_key_expiry(
        client,
        namespace=args.tenant,
        within_days=args.within_days,
        traverse=args.platform_wide,
        max_pages=args.max_pages,
        include_healthy=True,
    )
    client.close()

    rows = (
        all_rows
        if args.include_healthy
        else [
            row
            for row in all_rows
            if row.status in {"expired", "expiring_soon", "unknown"}
        ]
    )

    write_credential_expiry_csv(rows, output)
    summary = build_summary(
        args.tenant,
        within_days=args.within_days,
        rows=rows,
        raw_row_count=len(all_rows),
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

    if rows:
        print("\nKeys needing attention:")
        for row in rows[:10]:
            days = (
                str(row.days_until_expiry)
                if row.days_until_expiry is not None
                else "n/a"
            )
            print(
                f"  [{row.status}] {row.namespace}/{row.name} "
                f"(expires {row.expiration_time or 'unknown'}, days={days})"
            )
    else:
        print("No expired or soon-to-expire API keys matched the filters.")

    return 1 if summary["expired_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
