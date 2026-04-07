"""Unit tests for scripts/sync/baseline_ref."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_SYNC = _REPO_ROOT / "scripts" / "sync"
if str(_SCRIPTS_SYNC.parent) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_SCRIPTS_SYNC.parent))

from sync.baseline_ref import resolve_auto_baseline_ref  # noqa: E402


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_resolve_prefers_main_when_present(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _run_git(repo, "init", "-b", "main")
    _run_git(repo, "config", "user.email", "t@t.t")
    _run_git(repo, "config", "user.name", "t")
    (repo / "f").write_text("x", encoding="utf-8")
    _run_git(repo, "add", "f")
    _run_git(repo, "commit", "-m", "init")
    assert resolve_auto_baseline_ref(repo) == "main"


def test_resolve_prefers_master_when_main_missing(tmp_path: Path) -> None:
    repo = tmp_path / "r2"
    repo.mkdir()
    _run_git(repo, "init", "-b", "master")
    _run_git(repo, "config", "user.email", "t@t.t")
    _run_git(repo, "config", "user.name", "t")
    (repo / "f").write_text("x", encoding="utf-8")
    _run_git(repo, "add", "f")
    _run_git(repo, "commit", "-m", "init")
    assert resolve_auto_baseline_ref(repo) == "master"


def test_resolve_origin_main_when_local_branches_absent(tmp_path: Path) -> None:
    """Simulate clone: HEAD on feature; origin/main exists as remote-tracking ref."""
    bare = tmp_path / "bare.git"
    work = tmp_path / "work"
    bare.mkdir()
    work.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main", "--bare", str(bare)],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "clone", str(bare), str(work)],
        capture_output=True,
        check=True,
        cwd=tmp_path,
    )
    _run_git(work, "config", "user.email", "t@t.t")
    _run_git(work, "config", "user.name", "t")
    (work / "f").write_text("x", encoding="utf-8")
    _run_git(work, "add", "f")
    _run_git(work, "commit", "-m", "init")
    _run_git(work, "push", "-u", "origin", "main")
    _run_git(work, "checkout", "-b", "feature")
    (work / "f").write_text("y", encoding="utf-8")
    _run_git(work, "commit", "-am", "wip")
    assert resolve_auto_baseline_ref(work) == "origin/main"


def test_real_repo_returns_sensible_ref() -> None:
    """Smoke: endorlabs-sdk repo resolves to a non-empty ref."""
    if not (_REPO_ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    ref = resolve_auto_baseline_ref(_REPO_ROOT)
    assert ref in ("origin/main", "origin/master", "main", "master", "HEAD")
    proc = _run_git(_REPO_ROOT, "rev-parse", "--verify", f"{ref}^{{commit}}")
    assert proc.returncode == 0
