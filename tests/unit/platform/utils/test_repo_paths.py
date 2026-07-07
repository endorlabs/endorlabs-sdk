"""Unit tests for endorlabs.utils.repo_paths."""

from __future__ import annotations

from endorlabs.utils.repo_paths import normalize_repo_path, normalize_repo_paths


def test_normalize_repo_path() -> None:
    assert normalize_repo_path(" src\\foo\\bar.py ") == "src/foo/bar.py"
    assert normalize_repo_path("") is None
    assert normalize_repo_path("   ") is None


def test_normalize_repo_paths() -> None:
    assert normalize_repo_paths([" agent-knowledge\\", "", "README.md"]) == (
        "agent-knowledge",
        "README.md",
    )
