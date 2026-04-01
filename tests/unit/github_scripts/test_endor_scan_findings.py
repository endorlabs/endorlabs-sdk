"""Unit tests for .github/scripts/endor_scan_findings location extraction."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[3] / ".github" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import endor_scan_findings as esf


def test_extract_location_security_review_code_snippet() -> None:
    f = {
        "spec": {
            "finding_metadata": {
                "security_review_data": {
                    "code_snippet": {"file": "src/a.py", "line": 10, "line_end": 12}
                }
            }
        }
    }
    loc = esf.extract_location(f)
    assert loc["file"] == "src/a.py"
    assert loc["line"] == 10
    assert loc["line_end"] == 12


def test_extract_location_metadata_file_path_line_number() -> None:
    f = {
        "spec": {
            "finding_metadata": {
                "file_path": "b.py",
                "line_number": 3,
            }
        }
    }
    loc = esf.extract_location(f)
    assert loc["file"] == "b.py"
    assert loc["line"] == 3


def test_extract_location_custom_semgrep_shape() -> None:
    f = {
        "spec": {
            "finding_metadata": {
                "custom": {
                    "path": "pkg/x.py",
                    "start": {"line": 7},
                    "end": {"line": 9},
                }
            }
        }
    }
    loc = esf.extract_location(f)
    assert loc["file"] == "pkg/x.py"
    assert loc["line"] == 7
    assert loc["line_end"] == 9


def test_extract_location_dependency_file_paths_plus_custom_line() -> None:
    f = {
        "spec": {
            "dependency_file_paths": [".github/scripts/post_parallel_pr_comments.py"],
            "summary": "Issue in script",
            "finding_metadata": {
                "custom": {
                    "results": [
                        {
                            "path": ".github/scripts/post_parallel_pr_comments.py",
                            "start": {"line": 400},
                        }
                    ]
                }
            },
        }
    }
    loc = esf.extract_location(f)
    assert loc["file"] == ".github/scripts/post_parallel_pr_comments.py"
    assert loc["line"] == 400


def test_extract_location_dependency_paths_summary_line_fallback() -> None:
    f = {
        "spec": {
            "dependency_file_paths": ["src/foo.py"],
            "summary": "See src/foo.py:42 for details.",
        }
    }
    loc = esf.extract_location(f)
    assert loc["file"] == "src/foo.py"
    assert loc["line"] == 42


def test_summarize_location_coverage() -> None:
    findings = [
        {"spec": {"finding_metadata": {"file_path": "a.py", "line_number": 1}}},
        {"spec": {}},
    ]
    s = esf.summarize_location_coverage(findings)
    assert s["total"] == 2
    assert s["with_file_and_line"] == 1
    assert s["without_location"] == 1


def test_golden_fixture_json_roundtrip() -> None:
    """Golden list shape: what we expect the API + model_dump to be consumable."""
    raw = [
        {
            "uuid": "golden-1",
            "spec": {
                "finding_metadata": {
                    "custom": {
                        "path": "golden.py",
                        "start": {"line": 1},
                    }
                }
            },
        }
    ]
    assert esf.summarize_location_coverage(raw)["with_file_and_line"] == 1
    dumped = json.loads(json.dumps(raw))
    assert esf.extract_location(dumped[0])["line"] == 1
