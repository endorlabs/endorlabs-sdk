"""Shared path helpers for new-vs-resolved chart scripts."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def git_root(start: Path | None = None) -> Path | None:
    cwd = (start or Path.cwd()).resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    root = Path(result.stdout.strip())
    return root if root.is_dir() else None


def cursor_project_slug(root: Path) -> str:
    return str(root.resolve()).lstrip("/").replace("/", "-")


def resolve_canvas_dir(explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        explicit.mkdir(parents=True, exist_ok=True)
        return explicit

    env_dir = os.environ.get("CURSOR_CANVAS_DIR")
    if env_dir:
        path = Path(env_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    root = git_root()
    if root is None:
        return None

    candidate = (
        Path.home() / ".cursor" / "projects" / cursor_project_slug(root) / "canvases"
    )
    if candidate.parent.is_dir() or candidate.is_dir():
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    return None
