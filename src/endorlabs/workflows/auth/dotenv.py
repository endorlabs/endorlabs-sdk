"""Read and update local ``.env`` files for auth workflows (no secret logging)."""

from __future__ import annotations

import os
from pathlib import Path


def read_dotenv_value(env_path: Path, key: str) -> str | None:
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


def read_env_or_dotenv(key: str, env_file: Path) -> str | None:
    """Read ``key`` from process env, then from ``env_file``."""
    value = os.getenv(key)
    if value and value.strip():
        return value.strip()
    return read_dotenv_value(env_file, key)


def upsert_dotenv_key(env_path: Path, key: str, value: str) -> None:
    """Create or update a single ``key=value`` line in a dotenv file."""
    line = f"{key}={value}\n"
    if env_path.is_file():
        raw = env_path.read_text(encoding="utf-8")
        lines = raw.splitlines(keepends=True)
    else:
        lines = []

    prefix = f"{key}="
    idx = next((i for i, s in enumerate(lines) if s.startswith(prefix)), None)
    if idx is None:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] = lines[-1] + "\n"
        lines.append(line)
    else:
        lines[idx] = line

    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("".join(lines), encoding="utf-8")
