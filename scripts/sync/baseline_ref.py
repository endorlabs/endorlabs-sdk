"""Resolve a git baseline ref for model-sync delta comparisons."""

from __future__ import annotations

import subprocess
from pathlib import Path


def resolve_auto_baseline_ref(repo_root: Path) -> str:
    """Pick the first ref that resolves to a commit, else ``HEAD``.

    Tries ``origin/main``, ``origin/master``, ``main``, ``master`` in order so
    local feature branches compare against the likely default branch instead of
    ``HEAD`` (which would show no delta for uncommitted JSON).
    """
    for ref in ("origin/main", "origin/master", "main", "master"):
        if _ref_resolves(repo_root, ref):
            return ref
    return "HEAD"


def _ref_resolves(repo_root: Path, ref: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--verify", f"{ref}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0 and bool((proc.stdout or "").strip())
