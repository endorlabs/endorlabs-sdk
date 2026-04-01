"""Unit tests for .github/scripts/post_parallel_pr_comments helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parents[3] / ".github" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import post_parallel_pr_comments as ppc


def test_resolve_path_to_pr_file_exact() -> None:
    pr_files = {"src/foo.py", "README.md"}
    assert ppc.resolve_path_to_pr_file("src/foo.py", pr_files) == "src/foo.py"


def test_resolve_path_to_pr_file_basename_unique() -> None:
    pr_files = {"pkg/src/foo.py"}
    assert ppc.resolve_path_to_pr_file("foo.py", pr_files) == "pkg/src/foo.py"


def test_resolve_path_to_pr_file_basename_ambiguous() -> None:
    pr_files = {"a/foo.py", "b/foo.py"}
    assert ppc.resolve_path_to_pr_file("foo.py", pr_files) is None


def test_resolve_path_to_pr_file_missing() -> None:
    assert ppc.resolve_path_to_pr_file("nope.py", {"a.py"}) is None


def test_build_review_comment_object_single_line() -> None:
    finding = {
        "uuid": "u1",
        "spec": {
            "level": "FINDING_LEVEL_HIGH",
            "summary": "Bad thing",
            "finding_metadata": {},
        },
    }
    loc = {"file": "x.py", "line": 5, "line_end": None}
    obj = ppc.build_review_comment_object(
        finding,
        "o/r",
        "abc",
        "x.py",
        loc,
        "<!-- m -->",
    )
    assert obj is not None
    assert obj["path"] == "x.py"
    assert obj["line"] == 5
    assert obj["side"] == "RIGHT"
    assert "start_line" not in obj
    assert "<!-- m -->" in obj["body"]
    assert "Bad thing" in obj["body"]


def test_build_review_comment_object_multiline() -> None:
    finding = {"uuid": "u2", "spec": {"level": "LOW", "finding_metadata": {}}}
    loc = {"file": "z.py", "line": 2, "line_end": 4}
    obj = ppc.build_review_comment_object(
        finding,
        "o/r",
        "sha",
        "z.py",
        loc,
        "<!-- x -->",
    )
    assert obj is not None
    assert obj["start_line"] == 2
    assert obj["line"] == 4
    assert obj["start_side"] == "RIGHT"


def test_prepare_inline_comment_objects_respects_cap_and_dedupe() -> None:
    findings = [
        {
            "uuid": "a",
            "spec": {
                "finding_metadata": {
                    "security_review_data": {
                        "code_snippet": {"file": "f.py", "line": 1},
                    },
                },
            },
        },
        {
            "uuid": "b",
            "spec": {
                "finding_metadata": {
                    "security_review_data": {
                        "code_snippet": {"file": "f.py", "line": 2},
                    },
                },
            },
        },
    ]
    bodies = {"<!-- endorlabs-inhouse-finding:a:f.py:1 -->\nold"}
    objs, skipped, n_loc, n_un, snips = ppc.prepare_inline_comment_objects(
        findings,
        pr_files={"f.py"},
        existing_bodies=bodies,
        repo="o/r",
        commit_sha="c",
        max_inline=10,
        check_existing=True,
    )
    assert skipped == 0
    assert n_loc == 2
    assert n_un == 0
    assert len(objs) == 1
    assert len(snips) == 1
    assert "b" in objs[0]["body"] or "endorlabs-inhouse-finding:b:" in objs[0]["body"]


def test_code_region_fence_and_emit_smoke(capsys: Any) -> None:
    text = ppc._code_region_fence("src/x.py", 3, 5, "line1\nline2")
    assert "3:5:src/x.py" in text
    assert "line1" in text
    ppc.emit_inline_comment_plan_to_log(
        comment_objects=[
            {
                "path": "a.py",
                "line": 2,
                "side": "RIGHT",
                "body": "hello",
            }
        ],
        preview_snippets=["x = 1"],
    )
    out = capsys.readouterr().out
    assert "a.py" in out
    assert "2:2:a.py" in out
    assert "x = 1" in out
    assert "hello" in out
