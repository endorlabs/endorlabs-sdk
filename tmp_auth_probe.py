"""Temporary auth/permissions probe for demo troubleshooting.

Usage examples:
  uv run --no-sync python tmp_auth_probe.py --tenant endor-solutions-tgowan --auth-method api-key
  uv run --no-sync python tmp_auth_probe.py --tenant endor-solutions-tgowan --auth-method browser
  uv run --no-sync python tmp_auth_probe.py --tenant endor-solutions-tgowan --project-uuid 698cfb4f26aee2696691c78e

Notes:
  - This script is read-only by default (no scan trigger).
  - It helps compare principal identity/roles between browser vs api-key auth.
"""

from __future__ import annotations

import argparse
import contextlib
from typing import Any

import endorlabs
from endorlabs import F


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Temporary Endor auth probe")
    parser.add_argument("--tenant", required=True, help="Tenant namespace root")
    parser.add_argument(
        "--auth-method",
        choices=["api-key", "browser"],
        default="api-key",
        help="Authentication method to test",
    )
    parser.add_argument(
        "--project-uuid",
        default="",
        help="Optional project UUID for namespace/readability checks",
    )
    return parser.parse_args()


def _fmt(value: Any) -> str:
    return str(value) if value is not None else "<none>"


def main() -> None:
    args = _parse_args()
    client = endorlabs.Client(
        tenant=args.tenant,
        auth_method=args.auth_method,
        logging_level="ERROR",
    )

    try:
        print("\n== Auth Identity ==")
        identity = "<unknown>"
        with contextlib.suppress(Exception):
            identity = client.whoami() or "<unknown>"
        print(f"auth_method: {args.auth_method}")
        print(f"tenant:      {args.tenant}")
        print(f"whoami:      {identity}")

        print("\n== Authorization Policy ==")
        policy = None
        with contextlib.suppress(Exception):
            policy = client.authorization_policy.lookup(name=identity, traverse=True)
        if policy and policy.spec:
            perms = policy.spec.permissions
            roles = perms.roles if perms and perms.roles else []
            print(f"policy_uuid: {policy.uuid}")
            print(f"roles:       {roles}")
            print(f"expires:     {_fmt(policy.spec.expiration_time)}")
        else:
            print("authorization_policy lookup unavailable for this principal.")

        if args.project_uuid:
            print("\n== Project Scope Check ==")
            projects = client.project.list(
                filter=F("uuid") == args.project_uuid,
                traverse=True,
                max_pages=2,
                page_size=100,
            )
            if not projects:
                print(f"project {args.project_uuid} not visible in tenant scope.")
                return
            project = projects[0]
            pns = (
                project.tenant_meta.namespace
                if project.tenant_meta and project.tenant_meta.namespace
                else "<unknown-namespace>"
            )
            print(f"project_uuid: {project.uuid}")
            print(f"project_name: {project.meta.name if project.meta else '<unknown>'}")
            print(f"namespace:    {pns}")

            ns_client = endorlabs.Client(
                api_client=client._client,  # noqa: SLF001
                tenant=pns,
            )
            # Read-only probe for practical access boundary check.
            try:
                scans = ns_client.scan_result.list(parent=project, max_pages=1, page_size=1)
                print(f"read_scan_results: ok ({len(scans)} result(s) on first page)")
            except Exception as exc:
                print(f"read_scan_results: failed ({type(exc).__name__}: {exc})")

            print(
                "write_probe: skipped (this temp probe avoids mutating scan state). "
                "If needed, test write in demo by answering 'y' to trigger scan."
            )
    finally:
        client.close()


if __name__ == "__main__":
    main()
