#!/usr/bin/env python3
r"""Refresh ENDOR browser token via SSO and merge into a .env file (no secret output).

Mode defaults from ``ENDOR_AUTH_METHOD`` in the environment or ``--env-file``
(``admin`` → endor-admin SSO; otherwise tenant SSO). Override with ``--admin``
or ``--sso``.

Tenant SSO uses ``-n`` / ``--namespace``, then ``ENDOR_NAMESPACE``
(root tenant segment).

Run locally (opens browser; requires localhost:30000). Not for CI.

Examples::

    uv run --env-file .env python devtools/refresh_token_to_dotenv.py
    uv run --env-file .env python devtools/refresh_token_to_dotenv.py --sso
    uv run --env-file .env python devtools/refresh_token_to_dotenv.py --sso -n my-tenant
    uv run --env-file .env python devtools/refresh_token_to_dotenv.py --admin
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_NAMESPACE_ENV_KEY = "ENDOR_NAMESPACE"


def _read_dotenv_value(env_path: Path, key: str) -> str | None:
    """Return the value for ``key`` from a dotenv file, or ``None`` if absent."""
    if not env_path.is_file():
        return None
    prefix = f"{key}="
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or not line.startswith(prefix):
            continue
        value = line[len(prefix) :].strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        return value or None
    return None


def _read_env_value(key: str, env_file: Path) -> str | None:
    """Read ``key`` from process env, then from ``env_file``."""
    value = os.getenv(key)
    if value and value.strip():
        return value.strip()
    return _read_dotenv_value(env_file, key)


def _tenant_from_namespace(namespace: str) -> str:
    """Use the root tenant segment for SSO (``tenant.child`` → ``tenant``)."""
    cleaned = namespace.strip()
    if not cleaned:
        return ""
    return cleaned.split(".", 1)[0]


def resolve_auth_mode(
    *,
    admin: bool,
    sso: bool,
    env_file: Path,
) -> str:
    """Return ``admin`` or ``sso`` from flags or ``ENDOR_AUTH_METHOD`` env."""
    if admin and sso:
        raise SystemExit("--admin and --sso are mutually exclusive.")
    if admin:
        return "admin"
    if sso:
        return "sso"

    method = (_read_env_value("ENDOR_AUTH_METHOD", env_file) or "").lower()
    if method == "admin":
        return "admin"
    return "sso"


def resolve_auth_tenant(
    *,
    namespace: str | None,
    env_file: Path,
) -> str | None:
    """Resolve SSO tenant from ``-n`` / ``--namespace``, env, then ``env_file``."""
    if namespace and namespace.strip():
        return _tenant_from_namespace(namespace)

    value = _read_env_value(_NAMESPACE_ENV_KEY, env_file)
    if value:
        return _tenant_from_namespace(value)

    return None


def resolve_get_token_kwargs(
    *,
    admin: bool,
    sso: bool,
    namespace: str | None,
    env_file: Path,
    environment: str,
    timeout: int,
) -> dict[str, object]:
    """Build kwargs for ``endorlabs.auth_server.get_token`` from CLI options."""
    mode = resolve_auth_mode(admin=admin, sso=sso, env_file=env_file)
    if mode == "admin":
        return {
            "timeout": timeout,
            "environment": environment,
            "method": "admin",
        }

    tenant = resolve_auth_tenant(namespace=namespace, env_file=env_file)
    if not tenant:
        raise SystemExit(
            "Tenant SSO requires -n/--namespace or ENDOR_NAMESPACE "
            f"(in the environment or {env_file}). "
            "For endor-admin privileged read, pass --admin."
        )

    return {
        "timeout": timeout,
        "environment": environment,
        "method": "sso",
        "auth_tenant": tenant,
    }


def _merge_token_into_dotenv(env_path: Path, token: str) -> None:
    key_token = "ENDOR_TOKEN"
    line_token = f"{key_token}={token}\n"

    if env_path.is_file():
        raw = env_path.read_text(encoding="utf-8")
        lines = raw.splitlines(keepends=True)
    else:
        lines = []

    def upsert(key: str, line: str) -> None:
        prefix = f"{key}="
        idx = next((i for i, s in enumerate(lines) if s.startswith(prefix)), None)
        if idx is None:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] = lines[-1] + "\n"
            lines.append(line)
        else:
            lines[idx] = line

    upsert(key_token, line_token)

    env_path.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Browser SSO token refresh; writes ENDOR_TOKEN to .env. "
            "Mode defaults from ENDOR_AUTH_METHOD; tenant SSO uses env vars "
            "or -n/--namespace."
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Path to .env to create or update (default: .env)",
    )
    parser.add_argument(
        "--environment",
        default=None,
        help=(
            "API host segment for auth URL (default: from ENDOR_API or endorlabs.com)"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Seconds to wait for OAuth callback (default: 120)",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--admin",
        action="store_true",
        help="Use endor-admin SSO (elevated read).",
    )
    mode_group.add_argument(
        "--sso",
        action="store_true",
        help="Use tenant SSO (tenant from env vars or -n/--namespace).",
    )
    parser.add_argument(
        "-n",
        "--namespace",
        default=None,
        help=(
            "SSO tenant override for --sso or default tenant SSO. "
            "Fallback: ENDOR_NAMESPACE."
        ),
    )
    args = parser.parse_args()

    from endorlabs.auth_server import get_token

    environment = args.environment
    if not environment:
        api_base = _read_env_value("ENDOR_API", args.env_file) or "https://api.endorlabs.com"
        environment = api_base.replace("https://api.", "").replace("http://api.", "")
        if environment == api_base:
            environment = "endorlabs.com"

    token_kwargs = resolve_get_token_kwargs(
        admin=args.admin,
        sso=args.sso,
        namespace=args.namespace,
        env_file=args.env_file,
        environment=environment,
        timeout=args.timeout,
    )

    if token_kwargs["method"] == "admin":
        print(
            "Opening browser for endor-admin SSO (privileged read). "
            "Waiting for callback on localhost:30000...",
            file=sys.stderr,
        )
    else:
        tenant = token_kwargs["auth_tenant"]
        print(
            f"Opening browser for tenant SSO (tenant={tenant}). "
            "Waiting for callback on localhost:30000...",
            file=sys.stderr,
        )

    token = get_token(**token_kwargs)  # type: ignore[arg-type]
    if not token:
        print("Authentication failed or timed out.", file=sys.stderr)
        return 1

    _merge_token_into_dotenv(args.env_file, token)
    print(
        f"Updated {args.env_file.resolve()} (ENDOR_TOKEN set)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
