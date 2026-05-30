"""Unit tests for devtools/sync/baseline_ref."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS = _REPO_ROOT / "devtools"
if str(_DEVTOOLS) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_DEVTOOLS))

from sync.baseline_ref import resolve_auto_baseline_ref  # noqa: E402


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_real_repo_returns_sensible_ref() -> None:
    """Smoke: endorlabs-sdk repo resolves to a non-empty ref."""
    if not (_REPO_ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    ref = resolve_auto_baseline_ref(_REPO_ROOT)
    assert ref in ("origin/main", "origin/master", "main", "master", "HEAD")
    proc = _run_git(_REPO_ROOT, "rev-parse", "--verify", f"{ref}^{{commit}}")
    assert proc.returncode == 0
