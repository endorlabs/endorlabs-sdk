"""Endor Labs SDK walkthrough: list/get samples and create/update/delete examples.

Run from the repository (after ``uv sync``)::

    uv run python main.py

**Credentials:** set ``ENDOR_API_CREDENTIALS_KEY`` and ``ENDOR_API_CREDENTIALS_SECRET``
(or ``ENDOR_TOKEN``). Set ``ENDOR_NAMESPACE`` to your tenant namespace
(``tenant.namespace`` form).

This script is intentionally verbose and linear so you can follow each API call.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

from endorlabs import Client
from endorlabs.core.exceptions import EndorAPIError, PermissionDeniedError
from endorlabs.resources import policy
from endorlabs.resources.policy import (
    CreatePolicyPayload,
    ExceptionReason,
    PolicyType,
    UpdatePolicyPayload,
)
from endorlabs.resources.semgrep_rule import (
    CreateSemgrepRulePayload,
    SemgrepNativeRule,
    SemgrepRuleMetaCreate,
    SemgrepRuleSpec,
)


def _banner(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def _namespace_for(resource: Any, fallback: str) -> str:
    """Return the namespace string to use with ``get`` for this resource.

    Listed resources may live in a child namespace; ``get`` needs that exact path.
    """
    tenant_meta = getattr(resource, "tenant_meta", None)
    ns = getattr(tenant_meta, "namespace", None) if tenant_meta else None
    if isinstance(ns, str) and ns.strip():
        return ns
    return fallback


def demo_list_projects(client: Client) -> None:
    """``Project.list`` with pagination and tenant-wide traversal."""
    _banner("List projects (traverse=True)")
    try:
        projects = client.Project.list(traverse=True, max_pages=2, page_size=10)
    except EndorAPIError as exc:
        print(f"Could not list projects: {exc}")
        return
    print(f"Fetched {len(projects)} project(s) (up to 2 pages).")
    for p in projects[:5]:
        name = p.meta.name if p.meta else "(no name)"
        print(f"  - {name}  (uuid={p.uuid})")
    if len(projects) > 5:
        print(f"  ... and {len(projects) - 5} more")


def demo_list_and_get_finding(client: Client, default_namespace: str) -> None:
    """``Finding.list`` then ``Finding.get`` for the first result."""
    _banner("List findings, then get one by UUID")
    try:
        findings = client.Finding.list(traverse=True, max_pages=1, page_size=5)
    except EndorAPIError as exc:
        print(f"Could not list findings: {exc}")
        return
    if not findings:
        print("No findings returned (empty tenant or filters). Skipping get.")
        return
    first = findings[0]
    ns = _namespace_for(first, default_namespace)
    print(f"First finding uuid={first.uuid}  namespace={ns}")
    try:
        detail = client.Finding.get(first.uuid, namespace=ns)
    except EndorAPIError as exc:
        print(f"Could not get finding: {exc}")
        return
    title = getattr(detail.meta, "name", None) or "(no title)"
    print(f"GET succeeded: {title}")


def demo_list_api_keys(client: Client) -> None:
    """``APIKey.list`` — keys are sensitive; we only print names and uuid."""
    _banner("List API keys (metadata only)")
    try:
        keys = client.APIKey.list(max_pages=1, page_size=20)
    except EndorAPIError as exc:
        print(f"Could not list API keys: {exc}")
        return
    print(f"Fetched {len(keys)} key record(s).")
    for row in keys[:10]:
        name = row.meta.name if row.meta else "(no name)"
        print(f"  - {name}  uuid={row.uuid}")
    if len(keys) > 10:
        print(f"  ... and {len(keys) - 10} more")


def demo_semgrep_rule_create_and_delete(client: Client) -> None:
    """Create a small Semgrep rule, then remove it (cleanup)."""
    _banner("Create SemgrepRule, then delete it")
    rule_id = f"sdk-demo-rule-{int(time.time())}"
    payload = CreateSemgrepRulePayload(
        meta=SemgrepRuleMetaCreate(
            name=rule_id,
            description="Temporary rule created by main.py demo",
        ),
        spec=SemgrepRuleSpec(
            rule=SemgrepNativeRule(
                id=rule_id,
                languages=["python"],
                message="Demo: flag dangerous exec usage",
                pattern="exec($VAR)",
                severity="WARNING",
            )
        ),
        propagate=False,
    )
    created = None
    try:
        try:
            created = client.SemgrepRule.create(payload)
        except PermissionDeniedError as exc:
            print(f"Skipping create (no permission): {exc}")
            return
        print(f"Created SemgrepRule uuid={created.uuid} name={created.meta.name}")
    finally:
        if created is not None:
            try:
                client.SemgrepRule.delete(created.uuid)
                print(f"Deleted SemgrepRule uuid={created.uuid}")
            except EndorAPIError as exc:
                print(f"Cleanup delete failed (you may need to remove it in UI): {exc}")


def demo_policy_create_update_delete(client: Client, default_namespace: str) -> None:
    """Create an EXCEPTION policy, patch its description, then delete it."""
    _banner("Create Policy, update description, then delete")
    policy_name = f"SDK Demo Exception {int(time.time())}"
    # EXCEPTION policies use Rego + query_statements (see integration tests).
    create_payload = CreatePolicyPayload(
        meta=policy.PolicyMeta(
            name=policy_name,
            description="Temporary policy created by main.py demo",
            tags=["sdk-demo", "main-py"],
        ),
        spec=policy.PolicySpec(
            policy_type=PolicyType.EXCEPTION,
            rule="""package exceptions
match_finding[result] {
    some i
    data.resources.Finding[i]
    result = {"Endor": {"Finding": data.resources.Finding[i].uuid}}
}""",
            query_statements=["data.exceptions.match_finding"],
            disable=False,
            resource_kinds=["Finding"],
            exception={"reason": ExceptionReason.FALSE_POSITIVE},
        ),
        propagate=False,
    )
    created = None
    try:
        try:
            created = client.Policy.create(create_payload)
        except PermissionDeniedError as exc:
            print(f"Skipping policy create (no permission): {exc}")
            return
        except EndorAPIError as exc:
            print(f"Policy create failed: {exc}")
            return
        print(f"Created Policy uuid={created.uuid} name={created.meta.name}")

        update_payload = UpdatePolicyPayload(
            meta=policy.PolicyMetaUpdate(
                description="Updated once by main.py before delete.",
            ),
        )
        updated = client.Policy.update(
            created.uuid,
            update_payload,
            update_mask="meta.description",
            namespace=default_namespace,
        )
        print(f"Updated policy description on uuid={updated.uuid}")
    finally:
        if created is not None:
            try:
                client.Policy.delete(created.uuid)
                print(f"Deleted Policy uuid={created.uuid}")
            except EndorAPIError as exc:
                print(f"Cleanup delete failed: {exc}")


def main() -> int:
    """Run all demo sections against the live API."""
    tenant = os.environ.get("ENDOR_NAMESPACE", "").strip()
    if not tenant:
        print(
            "Set ENDOR_NAMESPACE to your tenant namespace "
            "(e.g. mycompany.dev). See README.md.",
        )
        return 1

    print(
        "Endor Labs SDK demo\n"
        f"Default namespace: {tenant}\n"
        "Using credentials from the environment (API key or token).",
    )

    with Client(tenant=tenant) as client:
        demo_list_projects(client)
        demo_list_and_get_finding(client, tenant)
        demo_list_api_keys(client)
        demo_semgrep_rule_create_and_delete(client)
        demo_policy_create_update_delete(client, tenant)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
