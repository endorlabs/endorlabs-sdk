"""AuthorizationPolicy normalize/list and claim→namespace mapping helpers.

Shared by skill scripts (SSO spot-check, AuthPolicy form audit). Prefer these
library entrypoints over copying policy extraction into session scripts.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from endorlabs import Client


class AuthorizationPolicyRecord(TypedDict, total=False):
    """Normalized AuthorizationPolicy fields for mapping and form audit."""

    uuid: str | None
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


def normalize_authorization_policy(policy: Any) -> AuthorizationPolicyRecord:
    """Extract policy fields into a normalized dictionary."""
    spec = getattr(policy, "spec", None)
    meta = getattr(policy, "meta", None)
    permissions = getattr(spec, "permissions", None)
    dump_permissions = getattr(permissions, "model_dump", dict)
    return {
        "uuid": getattr(policy, "uuid", None),
        "name": str(
            getattr(meta, "name", None) or getattr(policy, "uuid", "unknown-policy")
        ),
        "clause": list(getattr(spec, "clause", []) or []),
        "target_namespaces": list(getattr(spec, "target_namespaces", []) or []),
        "propagate": bool(getattr(spec, "propagate", False)),
        "permissions": dump_permissions() if permissions is not None else {},
        "namespace": getattr(getattr(policy, "tenant_meta", None), "namespace", None),
    }


def list_authorization_policies(
    client: Client,
    *,
    namespace: str,
    traverse: bool = False,
    max_pages: int | None = None,
) -> list[AuthorizationPolicyRecord]:
    """List and normalize AuthorizationPolicy rows for *namespace*."""
    kwargs: dict[str, Any] = {"namespace": namespace, "traverse": traverse}
    if max_pages is not None:
        kwargs["max_pages"] = max_pages
    policies = client.AuthorizationPolicy.list(**kwargs)
    return [normalize_authorization_policy(item) for item in policies]


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


def build_claim_namespace_map(
    policies: list[AuthorizationPolicyRecord] | list[dict[str, Any]],
) -> ClaimNamespaceReport:
    """Build claim-to-namespace and overlap report from policy-like dictionaries."""
    claims: dict[str, list[ClaimScopeEntry]] = defaultdict(list)
    namespace_to_claims: dict[str, set[str]] = defaultdict(set)

    for policy in policies:
        clause = list(policy.get("clause") or [])
        clause_key = _policy_clause_key(clause)
        target_namespaces = [str(ns) for ns in (policy.get("target_namespaces") or [])]
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
