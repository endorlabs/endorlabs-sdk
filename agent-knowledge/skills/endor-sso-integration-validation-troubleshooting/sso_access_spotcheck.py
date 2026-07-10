"""SSO claim-to-namespace access spot-check CLI (thin glue).

Library: ``endorlabs.workflows.auth.list_authorization_policies``,
``build_claim_namespace_map``, ``probe_auth_logs``.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.context.paths import default_runs_dir
from endorlabs.workflows.auth import (
    auth_log_snapshot,
    build_claim_namespace_map,
    filter_auth_logs_by_email,
    list_authorization_policies,
    probe_auth_logs,
)

RUN_BUCKET = "sso-integration-validation-troubleshooting"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _ = path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the spot-check command."""
    parser = argparse.ArgumentParser(
        description="Build claim-to-namespace SSO access spot-check report."
    )
    _ = parser.add_argument(
        "--tenant-hint",
        required=True,
        help="Tenant/root namespace hint.",
    )
    _ = parser.add_argument(
        "--target-email",
        default=None,
        help="Optional email to correlate.",
    )
    _ = parser.add_argument(
        "--target-group",
        action="append",
        default=[],
        help="Optional group claim filter (repeatable).",
    )
    _ = parser.add_argument(
        "--max-pages-policy",
        type=int,
        default=20,
        help="Pagination depth for AuthorizationPolicy listing.",
    )
    _ = parser.add_argument(
        "--max-pages-auth",
        type=int,
        default=50,
        help="Pagination depth for AuthenticationLog listing.",
    )
    _ = parser.add_argument(
        "--output-dir",
        default=str(default_runs_dir(RUN_BUCKET)),
        help=(
            "Output directory for JSON report files "
            f"(default: {default_runs_dir(RUN_BUCKET).as_posix()}/)."
        ),
    )
    return parser.parse_args()


def main() -> int:
    """Execute SSO access mapping and write report artifacts."""
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")

    client = endorlabs.Client(tenant=args.tenant_hint)
    try:
        policy_records = list_authorization_policies(
            client,
            namespace=args.tenant_hint,
            traverse=True,
            max_pages=args.max_pages_policy,
        )
        auth_rows_raw = probe_auth_logs(
            client,
            namespace=args.tenant_hint,
            max_pages=args.max_pages_auth,
            days=30,
        )
    finally:
        client.close()

    if args.target_email:
        auth_rows_raw = filter_auth_logs_by_email(auth_rows_raw, args.target_email)
    auth_rows = [auth_log_snapshot(row) for row in auth_rows_raw]

    report = build_claim_namespace_map(policy_records)

    if args.target_group:
        allowed_group_markers = {f"group={group}" for group in args.target_group}
        filtered_claims = {
            key: entries
            for key, entries in report.claims.items()
            if any(marker in key for marker in allowed_group_markers)
        }
    else:
        filtered_claims = report.claims

    report_payload: dict[str, Any] = {
        "generated_at": stamp,
        "tenant_hint": args.tenant_hint,
        "inputs": {
            "target_email": args.target_email,
            "target_group": args.target_group,
            "max_pages_policy": args.max_pages_policy,
            "max_pages_auth": args.max_pages_auth,
        },
        "claims": {
            key: [asdict(entry) for entry in entries]
            for key, entries in filtered_claims.items()
        },
        "overlap": asdict(report.overlap),
        "auth_log_sample": auth_rows,
        "notes": [
            "Authentication success and authorization scope are evaluated separately.",
            (
                "Root-targeted policy with propagate=false does not directly "
                "grant child namespace authorization."
            ),
            (
                "Root-context aggregate visibility can include child data "
                "without child namespace grant."
            ),
        ],
    }
    summary_payload: dict[str, Any] = {
        "generated_at": stamp,
        "tenant_hint": args.tenant_hint,
        "claims_count": len(filtered_claims),
        "overlap_namespace_count": len(report.overlap.direct_namespace_to_claim_keys),
        "auth_log_row_count": len(auth_rows),
    }

    report_path = output_dir / f"sso_access_spotcheck_report.{stamp}.json"
    summary_path = output_dir / f"sso_access_spotcheck_summary.{stamp}.json"
    _write_json(report_path, report_payload)
    _write_json(summary_path, summary_payload)
    _write_json(
        output_dir / f"sso_access_spotcheck_status.{stamp}.json",
        {
            "status": "ok",
            "report": str(report_path),
            "summary": str(summary_path),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
