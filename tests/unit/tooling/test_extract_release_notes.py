"""Unit tests for extract_release_notes."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _ROOT / "devtools" / "ship" / "extract_release_notes.py"


def _load():
    spec = importlib.util.spec_from_file_location("extract_release_notes", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_extract_changelog_section_for_published_release() -> None:
    mod = _load()
    body = mod.extract_changelog_section("0.7.0", root=_ROOT)
    assert "endor-reports" in body
    assert "### Added" in body


def test_format_release_notes_includes_compare_link() -> None:
    mod = _load()
    notes = mod.format_release_notes("0.7.0", root=_ROOT)
    assert "## endorlabs 0.7.0" in notes
    assert "compare/v0.6.0...v0.7.0" in notes
    assert "blob/v0.7.0/docs/changelog.md" in notes
