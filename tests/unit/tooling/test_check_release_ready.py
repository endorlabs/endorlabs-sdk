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


def _write_cut_tree(tmp_path: Path, *, version: str, unreleased_bullets: bool) -> Path:
    """Minimal pyproject + changelog for release-ready helper checks."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "endorlabs"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir(exist_ok=True)
    unreleased_body = (
        "### Added\n\n- pending feature\n\n"
        if unreleased_bullets
        else "### Added\n\n### Changed\n\n"
    )
    (docs / "changelog.md").write_text(
        f"## Unreleased\n\n{unreleased_body}## {version}\n\n### Added\n\n",
        encoding="utf-8",
    )
    return tmp_path


def test_changelog_helpers_detect_section_and_unreleased_bullets(
    tmp_path: Path,
) -> None:
    mod = _load()
    cut = _write_cut_tree(tmp_path, version="0.9.9", unreleased_bullets=False)
    assert mod.read_pyproject_version(root=cut) == "0.9.9"
    assert mod._changelog_has_section("0.9.9", root=cut)
    assert mod._unreleased_has_bullets(root=cut) is False

    dirty = _write_cut_tree(
        tmp_path / "dirty", version="0.9.9", unreleased_bullets=True
    )
    assert mod._unreleased_has_bullets(root=dirty) is True


def test_run_check_passes_for_synthetic_cut(tmp_path: Path) -> None:
    mod = _load()
    cut = _write_cut_tree(tmp_path, version="0.9.9", unreleased_bullets=False)
    assert mod.run_check(expect="0.9.9", skip_upstream=True, root=cut) == 0


def test_run_check_fails_when_unreleased_has_bullets(tmp_path: Path) -> None:
    mod = _load()
    dirty = _write_cut_tree(tmp_path, version="0.9.9", unreleased_bullets=True)
    assert mod.run_check(expect="0.9.9", skip_upstream=True, root=dirty) == 1


def test_run_check_fails_on_expect_mismatch() -> None:
    mod = _load()
    assert mod.run_check(expect="9.9.9", skip_upstream=True, root=_ROOT) == 1
