"""SSO claim-to-namespace access spot-check helper.

This script builds a customer-safe evidence report that maps authorization-policy
claim predicates to namespace scope, including propagation implications.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

import endorlabs
from endorlabs.context.paths import default_runs_dir


class PolicyRecord(TypedDict):
    """Normalized policy fields used for mapping."""

    name: str
    clause: list[str]
    target_namespaces: list[str]
    propagate: bool
    permissions: dict[str, Any]
    namespace: str | None


@dataclass(frozen=True)
class NamespaceScope:
    """Direct and propagated namespace implications for one policy."""

    direct_namespaces: list[str]
    propagated_namespace_prefixes: list[str]


@dataclass(frozen=True)
class ClaimScopeEntry:
    """Namespace scope contributed by one policy clause-set."""

    policy_name: str
    clause_key: str
    target_namespaces: list[str]
    propagate: bool
    direct_namespaces: list[str]
    propagated_namespace_prefixes: list[str]
    root_view_note: str


@dataclass(frozen=True)
class OverlapReport:
    """Overlap report for direct namespace grants."""

    direct_namespace_to_claim_keys: dict[str, list[str]]


@dataclass(frozen=True)
class ClaimNamespaceReport:
    """Normalized claim-to-namespace mapping report."""

    claims: dict[str, list[ClaimScopeEntry]]
    overlap: OverlapReport


def expand_namespace_scope(
    target_namespaces: list[str], *, propagate: bool
) -> NamespaceScope:
    """Compute direct and propagated namespace implications."""
    direct = sorted({ns.strip() for ns in target_namespaces if ns and ns.strip()})
    propagated = [f"{ns}.*" for ns in direct] if propagate else []
    return NamespaceScope(
        direct_namespaces=direct,
        propagated_namespace_prefixes=sorted(propagated),
    )


def _policy_clause_key(clause: list[str]) -> str:
    """Create stable key for a clause list."""
    cleaned = sorted(item.strip() for item in clause if item and item.strip())
    return " && ".join(cleaned) if cleaned else "(no-clause)"


def build_claim_namespace_map(policies: list[PolicyRecord]) -> ClaimNamespaceReport:
    """Build claim-to-namespace and overlap report from policy-like dictionaries."""
    claims: dict[str, list[ClaimScopeEntry]] = defaultdict(list)
    namespace_to_claims: dict[str, set[str]] = defaultdict(set)

    for policy in policies:
        clause = policy.get("clause") or []
        clause_key = _policy_clause_key(clause)
        target_namespaces = list(policy.get("target_namespaces") or [])
        propagate = bool(policy.get("propagate", False))
        scope = expand_namespace_scope(target_namespaces, propagate=propagate)

        entry = ClaimScopeEntry(
            policy_name=str(policy.get("name") or "unnamed-policy"),
            clause_key=clause_key,
            target_namespaces=scope.direct_namespaces,
            propagate=propagate,
            direct_namespaces=scope.direct_namespaces,
            propagated_namespace_prefixes=scope.propagated_namespace_prefixes,
            root_view_note=(
                "Root-context aggregate views may include child namespace data; "
                "this does not imply direct child-namespace authorization."
            ),
        )
        claims[clause_key].append(entry)
        for namespace in scope.direct_namespaces:
            namespace_to_claims[namespace].add(clause_key)

    overlap = {
        namespace: sorted(claim_keys)
        for namespace, claim_keys in sorted(namespace_to_claims.items())
        if len(claim_keys) > 1
    }
    return ClaimNamespaceReport(
        claims={k: v for k, v in sorted(claims.items())},
        overlap=OverlapReport(direct_namespace_to_claim_keys=overlap),
    )


def _extract_policy_record(policy: Any) -> PolicyRecord:
    """Extract policy fields into a normalized dictionary."""
    spec = getattr(policy, "spec", None)
    meta = getattr(policy, "meta", None)
    permissions = getattr(spec, "permissions", None)
    dump_permissions = getattr(permissions, "model_dump", dict)
    return {
        "name": (
            getattr(meta, "name", None) or getattr(policy, "uuid", "unknown-policy")
        ),
        "clause": list(getattr(spec, "clause", []) or []),
        "target_namespaces": list(getattr(spec, "target_namespaces", []) or []),
        "propagate": bool(getattr(spec, "propagate", False)),
        "permissions": dump_permissions(),
        "namespace": getattr(getattr(policy, "tenant_meta", None), "namespace", None),
    }


def _collect_authorization_policies(
    tenant_hint: str, *, max_pages_policy: int
) -> list[PolicyRecord]:
    """Collect policy records from tenant traversal."""
    client = endorlabs.Client(tenant=tenant_hint)
    policies = client.AuthorizationPolicy.list(
        traverse=True,
        max_pages=max_pages_policy,
    )
    records = [_extract_policy_record(item) for item in policies]
    client.close()

    return records


def _collect_authentication_log_rows(
    tenant_hint: str,
    target_email: str | None,
    *,
    max_pages_auth: int,
    days: int = 30,
) -> list[dict[str, Any]]:
    """Collect recent AuthenticationLog rows for optional correlation."""
    from endorlabs.workflows.auth import (
        auth_log_snapshot,
        filter_auth_logs_by_email,
        probe_auth_logs,
    )

    client = endorlabs.Client(tenant=tenant_hint)
    rows = probe_auth_logs(
        client,
        namespace=tenant_hint,
        max_pages=max_pages_auth,
        days=days,
    )
    client.close()
    if target_email:
        rows = filter_auth_logs_by_email(rows, target_email)
    return [auth_log_snapshot(row) for row in rows]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _ = path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


RUN_BUCKET = "sso-integration-validation-troubleshooting"


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

    policy_records = _collect_authorization_policies(
        args.tenant_hint,
        max_pages_policy=args.max_pages_policy,
    )
    report = build_claim_namespace_map(policy_records)
    auth_rows = _collect_authentication_log_rows(
        args.tenant_hint,
        args.target_email,
        max_pages_auth=args.max_pages_auth,
    )

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
