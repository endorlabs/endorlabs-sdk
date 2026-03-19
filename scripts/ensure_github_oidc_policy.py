"""Ensure GitHub Action OIDC auth policy exists for a tenant namespace.

Usage examples:
  uv run --env-file .env python scripts/ensure_github_oidc_policy.py --dry-run
  uv run --env-file .env python scripts/ensure_github_oidc_policy.py --apply
  uv run --env-file .env python scripts/ensure_github_oidc_policy.py --verify-only
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from typing import Any, cast

import endorlabs
from endorlabs.resources.authorization_policy import (
    AuthorizationPolicyMeta,
    AuthorizationPolicyPermissions,
    AuthorizationPolicySpec,
    CreateAuthorizationPolicyPayload,
    SystemRole,
)

logger = logging.getLogger(__name__)


@dataclass
class DesiredPolicy:
    """Normalized desired policy fields used for idempotency checks."""

    name: str
    claims: set[str]
    target_namespaces: set[str]
    role: str
    propagate: bool


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "--tenant",
        default="endor-solutions-tgowan",
        help="Root tenant namespace to authenticate and operate against.",
    )
    _ = parser.add_argument(
        "--namespace",
        default=None,
        help="Namespace where the auth policy is created (default: --tenant).",
    )
    _ = parser.add_argument(
        "--policy-name",
        default="github-oidc-code-scanner",
        help="Authorization policy name.",
    )
    _ = parser.add_argument(
        "--description",
        default="GitHub Action OIDC Code Scanner policy (managed by script).",
        help="Authorization policy description.",
    )
    _ = parser.add_argument(
        "--claim",
        action="append",
        dest="claims",
        default=[],
        help=(
            "Authorization clause entry, repeatable. "
            "Default claim is user=Endor-Solutions-Architecture."
        ),
    )
    _ = parser.add_argument(
        "--target-namespace",
        action="append",
        dest="target_namespaces",
        default=[],
        help="Target namespace entry, repeatable. Defaults to --tenant.",
    )
    _ = parser.add_argument(
        "--role",
        default=SystemRole.CODE_SCANNER.value,
        help="System role string for permissions.roles[0].",
    )
    _ = parser.add_argument(
        "--propagate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Propagate authorization policy to child namespaces.",
    )
    _ = parser.add_argument(
        "--apply",
        action="store_true",
        help="Create the policy when it does not exist.",
    )
    _ = parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Exit non-zero if matching policy is not found; never create.",
    )
    return parser.parse_args(argv)


def _normalize_claims(claims: list[str]) -> list[str]:
    normalized = [value.strip() for value in claims if value.strip()]
    if not normalized:
        normalized = ["github-action", "user=Endor-Solutions-Architecture"]
    normalized_set = set(normalized)
    normalized_set.add("github-action")
    return sorted(normalized_set)


def _normalize_target_namespaces(
    target_namespaces: list[str], tenant: str
) -> list[str]:
    normalized = [value.strip() for value in target_namespaces if value.strip()]
    if not normalized:
        return [tenant]
    return sorted(set(normalized))


def _extract_existing(existing: Any) -> DesiredPolicy | None:
    meta = getattr(existing, "meta", None)
    spec = getattr(existing, "spec", None)
    if meta is None or spec is None:
        return None
    name = getattr(meta, "name", None)
    if not isinstance(name, str):
        return None

    clause = getattr(spec, "clause", None)
    target_namespaces = getattr(spec, "target_namespaces", None)
    permissions = getattr(spec, "permissions", None)
    if not isinstance(clause, list) or not isinstance(target_namespaces, list):
        return None
    roles = getattr(permissions, "roles", None) if permissions is not None else None
    role = ""
    if isinstance(roles, list) and roles and isinstance(roles[0], str):
        role = roles[0]
    propagate = bool(getattr(spec, "propagate", False))
    clause_values = cast("list[object]", clause)
    target_values = cast("list[object]", target_namespaces)
    normalized_claims: set[str] = set()
    for raw_clause in clause_values:
        if isinstance(raw_clause, str):
            normalized_claims.add(raw_clause)
    normalized_targets: set[str] = set()
    for raw_target in target_values:
        if isinstance(raw_target, str):
            normalized_targets.add(raw_target)
    return DesiredPolicy(
        name=name,
        claims=normalized_claims,
        target_namespaces=normalized_targets,
        role=role,
        propagate=propagate,
    )


def _find_matching_policy(
    client: endorlabs.Client,
    namespace: str,
    desired: DesiredPolicy,
) -> Any | None:
    policies = client.authorization_policy.list(
        namespace=namespace,
        traverse=True,
        max_pages=10,
    )
    for policy in policies:
        existing = _extract_existing(policy)
        if existing is None:
            continue
        if (
            existing.name == desired.name
            and existing.claims == desired.claims
            and existing.target_namespaces == desired.target_namespaces
            and existing.role == desired.role
            and existing.propagate == desired.propagate
        ):
            return policy
    return None


def _emit_json(payload: dict[str, Any]) -> None:
    """Emit structured output in logs for CI and local scripts."""
    logger.info(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    """Ensure (or verify) a GitHub OIDC authorization policy."""
    args = _parse_args(argv or sys.argv[1:])
    namespace = args.namespace or args.tenant
    desired = DesiredPolicy(
        name=args.policy_name.strip(),
        claims=set(_normalize_claims(args.claims)),
        target_namespaces=set(
            _normalize_target_namespaces(args.target_namespaces, args.tenant)
        ),
        role=args.role.strip(),
        propagate=bool(args.propagate),
    )
    _emit_json(
        {
            "mode": (
                "verify-only"
                if args.verify_only
                else ("apply" if args.apply else "dry-run")
            ),
            "tenant": args.tenant,
            "namespace": namespace,
            "desired_policy": {
                "name": desired.name,
                "claims": sorted(desired.claims),
                "target_namespaces": sorted(desired.target_namespaces),
                "role": desired.role,
                "propagate": desired.propagate,
            },
        }
    )

    with endorlabs.Client(tenant=args.tenant) as client:
        existing = _find_matching_policy(client, namespace, desired)
        if existing is not None:
            _emit_json(
                {
                    "status": "exists",
                    "uuid": getattr(existing, "uuid", None),
                    "name": desired.name,
                }
            )
            return 0

        if args.verify_only:
            _emit_json(
                {
                    "status": "missing",
                    "error": "matching policy not found",
                }
            )
            return 2

        if not args.apply:
            _emit_json(
                {
                    "status": "dry-run",
                    "message": "policy would be created with --apply",
                }
            )
            return 0

        payload = CreateAuthorizationPolicyPayload(  # pyright: ignore[reportCallIssue]
            meta=AuthorizationPolicyMeta(  # pyright: ignore[reportCallIssue]
                name=desired.name,
                description=args.description.strip(),
            ),
            spec=AuthorizationPolicySpec(  # pyright: ignore[reportCallIssue]
                clause=sorted(desired.claims),
                target_namespaces=sorted(desired.target_namespaces),
                propagate=desired.propagate,
                permissions=AuthorizationPolicyPermissions(  # pyright: ignore[reportCallIssue]
                    roles=[desired.role]
                ),
            ),
            propagate=desired.propagate,
        )
        created = client.authorization_policy.create(payload, namespace=namespace)
        _emit_json(
            {
                "status": "created",
                "uuid": getattr(created, "uuid", None),
                "name": desired.name,
            }
        )
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
