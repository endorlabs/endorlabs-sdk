"""Create a GitHub Actions OIDC authorization policy in Endor Labs.

One-time setup script that creates an authorization policy allowing the
Endor-Solutions-Architecture GitHub org to authenticate via OIDC with
CODE_SCANNER permissions. Idempotent: skips creation if a matching policy
already exists.

Usage:
    uv run python scripts/setup_oidc_policy.py

Env:
    ENDOR_API_CREDENTIALS_KEY   - API key for admin authentication
    ENDOR_API_CREDENTIALS_SECRET - API secret for admin authentication
    ENDOR_NAMESPACE              - Target namespace (e.g. "endor-solutions-tgowan")
    ENDOR_API                    - (optional) API base URL
"""

from __future__ import annotations

import os
import sys

import endorlabs
from endorlabs.resources.authorization_policy import (
    AuthorizationPolicyMeta,
    AuthorizationPolicyPermissions,
    AuthorizationPolicySpec,
    CreateAuthorizationPolicyPayload,
    SystemRole,
)

# ── Configuration ─────────────────────────────────────────────────────────────
GITHUB_ORG = "Endor-Solutions-Architecture"
POLICY_NAME = f"GitHub Actions OIDC - {GITHUB_ORG}"
POLICY_DESCRIPTION = (
    f"Keyless authentication for GitHub Actions from the {GITHUB_ORG} org. "
    "Grants CODE_SCANNER role via GitHub OIDC identity provider."
)
OIDC_CLAUSE = f"user={GITHUB_ORG}"
ROLE = SystemRole.CODE_SCANNER


def main() -> None:
    """Create the OIDC authorization policy (idempotent)."""
    namespace = os.getenv("ENDOR_NAMESPACE")
    if not namespace:
        print("ERROR: ENDOR_NAMESPACE environment variable is required.")
        sys.exit(1)

    # Use the root (tenant) namespace for the policy so it covers all children
    tenant_root = namespace.split(".")[0]

    print(f"Namespace (tenant root): {tenant_root}")
    print(f"GitHub org:              {GITHUB_ORG}")
    print(f"Clause:                  {OIDC_CLAUSE}")
    print(f"Role:                    {ROLE.value}")
    print()

    client = endorlabs.Client(
        tenant=tenant_root,
        logging_level="WARNING",
        auth_method="api-key",
    )

    # ── Idempotency check ─────────────────────────────────────────────────────
    existing = client.authorization_policy.list(
        filter=f'meta.name=="{POLICY_NAME}"',
    )
    if existing:
        policy = existing[0]
        print(f"Policy already exists — skipping creation.")
        print(f"  UUID:       {policy.uuid}")
        print(f"  Name:       {policy.meta.name}")
        if policy.spec:
            print(f"  Clause:     {policy.spec.clause}")
            print(f"  Propagate:  {policy.spec.propagate}")
        return

    # ── Create the policy ─────────────────────────────────────────────────────
    payload = CreateAuthorizationPolicyPayload(
        meta=AuthorizationPolicyMeta(
            name=POLICY_NAME,
            description=POLICY_DESCRIPTION,
        ),
        spec=AuthorizationPolicySpec(
            clause=[OIDC_CLAUSE],
            target_namespaces=[tenant_root],
            propagate=True,
            permissions=AuthorizationPolicyPermissions(
                roles=[ROLE.value],
            ),
        ),
        propagate=True,
    )

    created = client.authorization_policy.create(payload)

    if created is None:
        print("ERROR: Authorization policy creation returned None.")
        sys.exit(1)

    print("Authorization policy created successfully.")
    print(f"  UUID:              {created.uuid}")
    print(f"  Name:              {created.meta.name}")
    if created.spec:
        print(f"  Clause:            {created.spec.clause}")
        print(f"  Target namespaces: {created.spec.target_namespaces}")
        print(f"  Propagate:         {created.spec.propagate}")
        if created.spec.permissions and created.spec.permissions.roles:
            print(f"  Roles:             {created.spec.permissions.roles}")


if __name__ == "__main__":
    main()
