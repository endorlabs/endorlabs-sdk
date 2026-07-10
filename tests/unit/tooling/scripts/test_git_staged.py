"""Unit tests for devtools/precommit/git_staged.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS = _REPO_ROOT / "devtools" / "precommit"
if str(_DEVTOOLS) not in sys.path:
    sys.path.insert(0, str(_DEVTOOLS))

from git_staged import staged_added_lines, staged_paths  # noqa: E402


@patch(
    "git_staged.subprocess.run",
    return_value=type(
        "R",
        (),
        {"returncode": 0, "stdout": "README.md\n.env\n", "stderr": ""},
    )(),
)
def test_staged_paths_normalizes_and_skips_blank(mock_run: object) -> None:
    assert staged_paths() == ["README.md", ".env"]
    assert mock_run is not None


@patch(
    "git_staged.subprocess.run",
    return_value=type(
        "R",
        (),
        {
            "returncode": 0,
            "stdout": (
                "diff --git a/docs/a.md b/docs/a.md\n"
                "--- a/docs/a.md\n"
                "+++ b/docs/a.md\n"
                "@@ -1,0 +2,2 @@\n"
                "+" + "user@" + "customer.com" + "\n"
                "+https://docs.endorlabs.com/x\n"
                " unchanged\n"
            ),
            "stderr": "",
        },
    )(),
)
def test_staged_added_lines_parses_hunks(mock_run: object) -> None:
    rows = staged_added_lines()
    assert rows == [
        ("docs/a.md", 2, "user@" + "customer.com"),
        ("docs/a.md", 3, "https://docs.endorlabs.com/x"),
    ]
    assert mock_run is not None


@patch(
    "git_staged.subprocess.run",
    return_value=type(
        "R",
        (),
        {"returncode": 1, "stdout": "", "stderr": "not a git repo"},
    )(),
)
def test_staged_paths_raises_on_git_failure(mock_run: object) -> None:
    try:
        staged_paths()
    except RuntimeError as exc:
        assert "git diff --cached failed" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
    assert mock_run is not None
