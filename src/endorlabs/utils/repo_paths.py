"""Repo-relative path normalization for git hooks and maintainer tooling."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import PurePosixPath


def normalize_repo_path(raw: str) -> str | None:
    """Return a POSIX repo-relative path, or ``None`` when *raw* is empty."""
    cleaned = raw.strip().replace("\\", "/")
    if not cleaned:
        return None
    return PurePosixPath(cleaned).as_posix()


def normalize_repo_paths(paths: Sequence[str]) -> tuple[str, ...]:
    """Normalize hook/git paths for prefix matching."""
    normalized: list[str] = []
    for raw_path in paths:
        cleaned = normalize_repo_path(raw_path)
        if cleaned is not None:
            normalized.append(cleaned)
    return tuple(normalized)
