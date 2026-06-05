"""Repo-root discovery and safe output paths for model-sync."""

from __future__ import annotations

import re
from pathlib import Path

REPO_MARKERS = ("pyproject.toml", "src/endorlabs")

_MODULE_SEGMENT_RE = re.compile(r"^[a-z0-9_]+(?:/[a-z0-9_]+)*$")


def find_repo_root(*, start: Path | None = None) -> Path:
    """Walk parents from *start* (default cwd) until repo markers exist."""
    candidates: list[Path] = []
    if start is not None:
        candidates.append(start.resolve())
    else:
        candidates.append(Path.cwd().resolve())
    here = Path(__file__).resolve()
    candidates.append(here.parent)
    seen: set[Path] = set()
    for origin in candidates:
        current = origin
        while current not in seen:
            seen.add(current)
            if all((current / marker).exists() for marker in REPO_MARKERS):
                return current
            parent = current.parent
            if parent == current:
                break
            current = parent
    raise RuntimeError(
        "Could not find repository root (expected pyproject.toml and src/endorlabs). "
        "Run model-sync from the endorlabs-sdk checkout."
    )


def assert_under_root(path: Path, root: Path) -> Path:
    """Resolve *path* and ensure it is contained under *root*."""
    resolved = path.resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as error:
        raise ValueError(
            f"Path {resolved} is outside repository root {root_resolved}"
        ) from error
    return resolved


def safe_module_segment(module_path: str) -> str:
    """Reject traversal segments; allow ``[a-z0-9_/]`` module paths only."""
    normalized = module_path.replace("\\", "/").strip("/")
    if not normalized or ".." in normalized.split("/"):
        raise ValueError(f"Unsafe module path: {module_path!r}")
    if normalized.startswith("/") or ":" in normalized:
        raise ValueError(f"Unsafe module path: {module_path!r}")
    if not _MODULE_SEGMENT_RE.fullmatch(normalized):
        raise ValueError(f"Unsafe module path: {module_path!r}")
    return normalized


def safe_repo_output_path(root: Path, *parts: str) -> Path:
    """Join *parts* under *root* and verify containment."""
    joined = root.joinpath(*parts)
    return assert_under_root(joined, root)
