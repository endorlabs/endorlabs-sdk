"""Shared path helpers for PRF report scripts."""

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


def resolve_chrome(explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        return explicit if explicit.is_file() else None

    env_path = os.environ.get("CHROME_PATH") or os.environ.get("GOOGLE_CHROME_BIN")
    if env_path:
        path = Path(env_path)
        if path.is_file():
            return path

    candidates = [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/usr/bin/google-chrome"),
        Path("/usr/bin/chromium"),
        Path("/usr/bin/chromium-browser"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None
