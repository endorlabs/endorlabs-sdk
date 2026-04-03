"""Unit tests for .github/scripts/post_github_check_run.py helpers."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[3] / ".github" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import post_github_check_run as pgc


def test_maybe_append_smoke_annotation_disabled() -> None:
    base = [
        {"path": "a.py", "start_line": 1, "end_line": 1, "annotation_level": "notice"}
    ]
    out = pgc.maybe_append_smoke_annotation(
        base, do_append=False, smoke_path="pyproject.toml", smoke_line=1
    )
    assert out is base


def test_maybe_append_smoke_annotation_appends() -> None:
    out = pgc.maybe_append_smoke_annotation(
        [], do_append=True, smoke_path="pyproject.toml", smoke_line=2
    )
    assert len(out) == 1
    assert out[0]["path"] == "pyproject.toml"
    assert out[0]["start_line"] == 2
    assert out[0]["end_line"] == 2
    assert out[0]["annotation_level"] == "notice"
    assert out[0]["title"] == "Smoke (opt-in)"


def test_maybe_append_smoke_annotation_coerces_line_below_one() -> None:
    out = pgc.maybe_append_smoke_annotation(
        [], do_append=True, smoke_path="pyproject.toml", smoke_line=0
    )
    assert out[0]["start_line"] == 1


def test_maybe_append_smoke_annotation_skips_invalid_path() -> None:
    out = pgc.maybe_append_smoke_annotation(
        [{"path": "x"}], do_append=True, smoke_path=".", smoke_line=1
    )
    assert len(out) == 1
    assert out[0]["path"] == "x"


def test_smoke_annotation_requested_cli_flag() -> None:
    assert pgc.smoke_annotation_requested(cli_flag=True) is True


def test_smoke_annotation_requested_env(monkeypatch: object) -> None:
    monkeypatch.delenv("ENDOR_GITHUB_CHECK_SMOKE", raising=False)
    assert pgc.smoke_annotation_requested(cli_flag=False) is False
    monkeypatch.setenv("ENDOR_GITHUB_CHECK_SMOKE", "1")
    assert pgc.smoke_annotation_requested(cli_flag=False) is True
    monkeypatch.setenv("ENDOR_GITHUB_CHECK_SMOKE", "true")
    assert pgc.smoke_annotation_requested(cli_flag=False) is True


def test_build_annotations_from_fixture() -> None:
    finding = {
        "uuid": "u1",
        "meta": {"name": "RuleA"},
        "spec": {
            "level": "FINDING_LEVEL_HIGH",
            "summary": "bad",
            "finding_metadata": {
                "file_path": "src/x.py",
                "line_number": 5,
            },
        },
    }
    anns = pgc.build_annotations([finding])
    assert len(anns) == 1
    assert anns[0]["path"] == "src/x.py"
    assert anns[0]["start_line"] == 5
    assert anns[0]["annotation_level"] == "failure"
