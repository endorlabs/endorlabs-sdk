#!/usr/bin/env python3
"""Run a command with .env loaded but ENDOR_TOKEN omitted (API key auth).

Use when ENDOR_TOKEN is expired but ENDOR_API_CREDENTIALS_* are valid for
**your own** tenant. Customer cross-tenant list/get usually still needs a fresh
Customer cross-tenant list/get may need a fresh bearer token for that tenant
(see ``uv run endor-auth refresh --method sso -n <tenant>``).

Injects ``--no-env-file`` after each ``uv run`` so nested ``uv`` does not reload
a stale ``ENDOR_TOKEN`` from disk. Does not print secrets.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def _load_env_without_token(env_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    if not env_path.is_file():
        return env
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key == "ENDOR_TOKEN":
            continue
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        env[key] = value
    env.pop("ENDOR_TOKEN", None)
    return env


def _inject_uv_no_env_file(cmd: list[str]) -> list[str]:
    """Insert ``--no-env-file`` after every ``uv run`` token pair."""
    out: list[str] = []
    i = 0
    while i < len(cmd):
        if i + 1 < len(cmd) and cmd[i] == "uv" and cmd[i + 1] == "run":
            out.extend(["uv", "run"])
            i += 2
            if i < len(cmd) and cmd[i] == "--no-env-file":
                out.append("--no-env-file")
                i += 1
            else:
                out.append("--no-env-file")
            continue
        out.append(cmd[i])
        i += 1
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Dotenv file (default: .env)",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command after -- (e.g. -- uv run endor-estate analyze -n tenant.example)",
    )
    args = parser.parse_args()
    cmd = args.command
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        parser.error("command required after --")
    env = _load_env_without_token(args.env_file.resolve())
    cmd = _inject_uv_no_env_file(cmd)
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
