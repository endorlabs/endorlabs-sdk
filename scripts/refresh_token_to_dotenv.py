#!/usr/bin/env python3
r"""Refresh ENDOR browser token via SSO and merge into a .env file (no secret output).

Uses ``endorlabs.auth_server.get_token`` with ``method="admin"`` (endor-admin SSO).
Run locally (opens browser; requires localhost:30000). Not for CI.

Example::

    uv run python scripts/refresh_token_to_dotenv.py
    uv run python scripts/refresh_token_to_dotenv.py --env-file .env --timeout 180
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _merge_token_into_dotenv(
    env_path: Path,
    token: str,
    *,
    also_admin_alias: bool = True,
) -> None:
    key_token = "ENDOR_TOKEN"
    key_admin = "ENDOR_ADMIN_TOKEN"
    line_token = f"{key_token}={token}\n"
    line_admin = f"{key_admin}={token}\n"

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
    if also_admin_alias:
        upsert(key_admin, line_admin)

    env_path.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Browser SSO token refresh; writes ENDOR_TOKEN "
            "(and ENDOR_ADMIN_TOKEN) to .env."
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
        default="endorlabs.com",
        help=(
            "API host segment for auth URL "
            "(default: endorlabs.com → api.endorlabs.com)"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Seconds to wait for OAuth callback (default: 120)",
    )
    parser.add_argument(
        "--no-admin-alias",
        action="store_true",
        help="Do not write ENDOR_ADMIN_TOKEN (only ENDOR_TOKEN)",
    )
    args = parser.parse_args()

    from endorlabs.auth_server import get_token

    print(
        "Opening browser for SSO. Complete login; "
        "waiting for callback on localhost:30000...",
        file=sys.stderr,
    )
    token = get_token(
        timeout=args.timeout,
        environment=args.environment,
        method="admin",
    )
    if not token:
        print("Authentication failed or timed out.", file=sys.stderr)
        return 1

    _merge_token_into_dotenv(
        args.env_file,
        token,
        also_admin_alias=not args.no_admin_alias,
    )
    print(f"Updated {args.env_file.resolve()} (ENDOR_TOKEN set)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
