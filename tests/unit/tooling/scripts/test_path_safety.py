"""Unit tests for model-sync path safety helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS_DIR = str(_REPO_ROOT / "devtools")
if _DEVTOOLS_DIR not in sys.path:
    sys.path.insert(0, _DEVTOOLS_DIR)

from sync.path_safety import (  # noqa: E402
    assert_under_root,
    find_repo_root,
    safe_module_segment,
    safe_repo_output_path,
)


def test_find_repo_root_from_test_file() -> None:
    root = find_repo_root(start=_REPO_ROOT)
    assert (root / "pyproject.toml").is_file()
    assert (root / "src" / "endorlabs").is_dir()


def test_assert_under_root_accepts_relative_child() -> None:
    root = find_repo_root()
    child = safe_repo_output_path(root, "src", "endorlabs", "generated", "models")
    assert_under_root(child, root)


def test_assert_under_root_rejects_escape(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError, match="outside repository root"):
        assert_under_root(outside, root)


def test_safe_module_segment_rejects_traversal() -> None:
    with pytest.raises(ValueError, match="Unsafe module path"):
        safe_module_segment("../escape")
    with pytest.raises(ValueError, match="Unsafe module path"):
        safe_module_segment("foo/../bar")


def test_safe_module_segment_accepts_nested() -> None:
    assert safe_module_segment("core/base") == "core/base"


def test_safe_repo_output_path_rejects_traversal_part() -> None:
    root = find_repo_root()
    with pytest.raises(ValueError, match="outside repository root"):
        safe_repo_output_path(root, "..", "etc", "passwd")
