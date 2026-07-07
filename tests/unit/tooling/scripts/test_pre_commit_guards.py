"""Unit tests for devtools/pre_commit_guards.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS = _REPO_ROOT / "devtools"
if str(_DEVTOOLS) not in sys.path:
    sys.path.insert(0, str(_DEVTOOLS))

from pre_commit_guards import (  # noqa: E402
    check_blocked_staged_paths,
    check_changelog_reminder,
    is_blocked_staged_path,
    is_user_facing_staged_path,
)


def test_is_blocked_staged_path() -> None:
    assert is_blocked_staged_path(".env")
    assert is_blocked_staged_path(".endorlabs-context/sdk/INDEX.md")
    assert not is_blocked_staged_path("README.md")
    assert not is_blocked_staged_path("src/endorlabs/__init__.py")


def test_is_user_facing_staged_path() -> None:
    assert is_user_facing_staged_path("README.md")
    assert is_user_facing_staged_path("src/endorlabs/client.py")
    assert is_user_facing_staged_path("agent-knowledge/skills/foo/SKILL.md")
    assert is_user_facing_staged_path("docs/guides/examples.md")
    assert not is_user_facing_staged_path("docs/generated-reference/resources.md")
    assert not is_user_facing_staged_path("src/endorlabs/generated/models/foo.py")
    assert not is_user_facing_staged_path("tests/unit/test_foo.py")
    assert not is_user_facing_staged_path("docs/changelog.md")
    assert not is_user_facing_staged_path("CONTRIBUTORS.md")


@patch("pre_commit_guards.staged_paths", return_value=[".env"])
def test_check_blocked_staged_paths_fails(mock_staged_paths: object) -> None:
    assert check_blocked_staged_paths() == 1
    assert mock_staged_paths is not None


@patch(
    "pre_commit_guards.staged_paths",
    return_value=[".endorlabs-context/workspace/runs/foo.json"],
)
def test_check_blocked_staged_paths_context(mock_staged_paths: object) -> None:
    assert check_blocked_staged_paths() == 1
    assert mock_staged_paths is not None


@patch("pre_commit_guards.staged_paths", return_value=["README.md"])
def test_check_blocked_staged_paths_ok(mock_staged_paths: object) -> None:
    assert check_blocked_staged_paths() == 0
    assert mock_staged_paths is not None


@patch(
    "pre_commit_guards.staged_paths",
    return_value=["src/endorlabs/workflows/auth/cli.py"],
)
def test_check_changelog_reminder_prints(mock_staged_paths: object, capsys) -> None:
    assert check_changelog_reminder() == 0
    err = capsys.readouterr().err
    assert "reminder:" in err
    assert "docs/changelog.md" in err
    assert mock_staged_paths is not None


@patch(
    "pre_commit_guards.staged_paths",
    return_value=["src/endorlabs/workflows/auth/cli.py", "docs/changelog.md"],
)
def test_check_changelog_reminder_silent_when_changelog_staged(
    mock_staged_paths: object,
) -> None:
    assert check_changelog_reminder() == 0
    assert mock_staged_paths is not None


@patch("pre_commit_guards.staged_paths", return_value=["tests/unit/test_foo.py"])
def test_check_changelog_reminder_silent_for_tests(mock_staged_paths: object) -> None:
    assert check_changelog_reminder() == 0
    assert mock_staged_paths is not None
