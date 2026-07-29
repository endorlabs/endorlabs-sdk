"""AuthorizationPolicy form-audit CLI (thin glue).

Library: ``endorlabs.workflows.auth.list_authorization_policies``,
``audit_authorization_policy_forms``.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import endorlabs
from endorlabs.context.paths import default_runs_dir
from endorlabs.workflows.auth import (
    audit_authorization_policy_forms,
    list_authorization_policies,
)

RUN_BUCKET = "audit-authorization-policies"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit AuthorizationPolicy claim/namespace form."
    )
    _ = parser.add_argument(
        "--tenant-hint",
        required=True,
        help="Tenant root (or child) namespace to list AuthorizationPolicy from.",
    )
    _ = parser.add_argument(
        "--traverse",
        action="store_true",
        help="List with traverse=True (policies under child namespaces).",
    )
    _ = parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional list pagination cap.",
    )
    _ = parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for auth_policy_form_audit.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry."""
    args = _parse_args(argv)
    out_dir = args.output_dir or default_runs_dir(RUN_BUCKET)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = endorlabs.Client(tenant=args.tenant_hint)
    try:
        records = list_authorization_policies(
            client,
            namespace=args.tenant_hint,
            traverse=bool(args.traverse),
            max_pages=args.max_pages,
        )
    finally:
        client.close()

    findings = audit_authorization_policy_forms(list(records))
    by_severity = {
        "critical": sum(1 for f in findings if f.severity == "critical"),
        "warning": sum(1 for f in findings if f.severity == "warning"),
        "info": sum(1 for f in findings if f.severity == "info"),
    }
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "tenant_hint": args.tenant_hint,
        "traverse": bool(args.traverse),
        "policy_count": len(records),
        "finding_counts": by_severity,
        "findings": [asdict(f) for f in findings],
        "policies_scanned": [
            {
                "uuid": r.get("uuid"),
                "name": r.get("name"),
                "namespace": r.get("namespace"),
                "clause": r.get("clause"),
                "target_namespaces": r.get("target_namespaces"),
                "propagate": r.get("propagate"),
            }
            for r in records
        ],
    }
    out_path = out_dir / "auth_policy_form_audit.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {out_path} policies={report['policy_count']} "
        f"critical={by_severity['critical']} warning={by_severity['warning']} "
        f"info={by_severity['info']}"
    )
    return 0 if by_severity["critical"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
