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


def test_development_state_keeps_unreleased_bullets() -> None:
    mod = _load()
    assert mod._changelog_has_section("0.7.0", root=_ROOT)
    assert mod._unreleased_has_bullets(root=_ROOT) is True
    assert mod._changelog_has_section("0.8.0", root=_ROOT) is False


def test_run_check_fails_while_unreleased_has_bullets() -> None:
    mod = _load()
    assert mod.run_check(expect="0.7.0", skip_upstream=True, root=_ROOT) == 1
