"""Git staged-path helpers for pre-commit and devtools entrypoints.

Policy checks belong in ``pre_commit_guards.py``; this module only lists and
normalizes staged paths. Shared normalization lives in ``endorlabs.utils.repo_paths``.
"""

from __future__ import annotations

import subprocess

from endorlabs.utils.repo_paths import normalize_repo_path

__all__ = ["normalize_repo_path", "staged_paths"]


def staged_paths(*, diff_filter: str = "ACMR") -> list[str]:
    """Return POSIX paths staged for commit (``git diff --cached --name-only``)."""
    result = subprocess.run(  # noqa: S603
        ["git", "diff", "--cached", "--name-only", f"--diff-filter={diff_filter}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        msg = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"git diff --cached failed: {msg}")
    paths: list[str] = []
    for line in result.stdout.splitlines():
        normalized = normalize_repo_path(line)
        if normalized is not None:
            paths.append(normalized)
    return paths
