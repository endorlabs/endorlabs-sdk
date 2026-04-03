"""Unit tests for .github/scripts/smoke_github_check_annotation.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[3] / ".github" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import smoke_github_check_annotation as sgc


def test_build_smoke_check_run_body_default() -> None:
    body = sgc.build_smoke_check_run_body(
        head_sha="abc1234",
        path="pyproject.toml",
        line=1,
    )
    assert body["name"] == sgc._DEFAULT_CHECK_NAME
    assert body["head_sha"] == "abc1234"
    assert body["status"] == "completed"
    assert body["conclusion"] == "success"
    anns = body["output"]["annotations"]
    assert len(anns) == 1
    a0 = anns[0]
    assert a0["path"] == "pyproject.toml"
    assert a0["start_line"] == 1
    assert a0["end_line"] == 1
    assert a0["annotation_level"] == "notice"
    assert "message" in a0
    assert a0["title"] == "Smoke"


def test_build_smoke_check_run_body_normalizes_diff_prefix() -> None:
    body = sgc.build_smoke_check_run_body(head_sha="x", path="a/src/foo.py", line=3)
    assert body["output"]["annotations"][0]["path"] == "src/foo.py"
    assert body["output"]["annotations"][0]["start_line"] == 3


def test_build_smoke_check_run_body_rejects_invalid_path() -> None:
    with pytest.raises(ValueError, match="Invalid"):
        sgc.build_smoke_check_run_body(head_sha="x", path=".", line=1)


def test_build_smoke_check_run_body_rejects_line_zero() -> None:
    with pytest.raises(ValueError, match="line"):
        sgc.build_smoke_check_run_body(head_sha="x", path="pyproject.toml", line=0)
