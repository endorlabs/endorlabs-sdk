"""Unit tests for check_release_ready preflight."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _ROOT / "devtools" / "ship" / "check_release_ready.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_release_ready", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cut_state_has_version_section_and_empty_unreleased() -> None:
    """After a release cut, Unreleased has no bullets and ## X.Y.Z exists."""
    mod = _load()
    version = mod.read_pyproject_version(root=_ROOT)
    assert version is not None
    assert mod._changelog_has_section(version, root=_ROOT)
    assert mod._unreleased_has_bullets(root=_ROOT) is False
    assert mod._changelog_has_section("0.7.0", root=_ROOT)


def test_run_check_passes_for_cut_version() -> None:
    mod = _load()
    version = mod.read_pyproject_version(root=_ROOT)
    assert version is not None
    assert mod.run_check(expect=version, skip_upstream=True, root=_ROOT) == 0


def test_run_check_fails_on_expect_mismatch() -> None:
    mod = _load()
    assert mod.run_check(expect="9.9.9", skip_upstream=True, root=_ROOT) == 1
