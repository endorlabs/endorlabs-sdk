"""Unit tests for devtools/ship/check_project_version.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS = _REPO_ROOT / "devtools" / "ship"
if str(_DEVTOOLS) not in sys.path:
    sys.path.insert(0, str(_DEVTOOLS))

from check_project_version import (  # noqa: E402
    read_pyproject_version,
    run_check,
    warn_legacy_dev0_tags,
)


def test_warn_legacy_dev0_tags_flags_dev0_anchor(capsys) -> None:
    warn_legacy_dev0_tags(["v0.6.1.dev0", "v0.6.0"])
    captured = capsys.readouterr()
    assert "v0.6.1.dev0" in captured.err
    assert "v0.6.0" not in captured.err


def test_read_pyproject_version_returns_static_version() -> None:
    version = read_pyproject_version(root=_REPO_ROOT)
    assert version is not None
    assert version.count(".") >= 2


def test_run_check_expect_match() -> None:
    version = read_pyproject_version(root=_REPO_ROOT)
    assert version is not None
    with (
        patch("check_project_version._list_local_tags", return_value=[]),
        patch(
            "check_project_version.resolve_uv_version",
            return_value=version,
        ),
    ):
        assert run_check(expect=version, warn_tags=False) == 0


def test_run_check_expect_mismatch() -> None:
    with (
        patch("check_project_version._list_local_tags", return_value=[]),
        patch(
            "check_project_version.read_pyproject_version",
            return_value="0.6.0",
        ),
        patch(
            "check_project_version.resolve_uv_version",
            return_value="0.6.0",
        ),
    ):
        assert run_check(expect="9.9.9", warn_tags=False) == 1


def test_run_check_skips_tag_scan_when_disabled() -> None:
    version = read_pyproject_version(root=_REPO_ROOT)
    assert version is not None
    with (
        patch("check_project_version._list_local_tags") as list_tags,
        patch(
            "check_project_version.resolve_uv_version",
            return_value=version,
        ),
    ):
        assert run_check(expect=version, warn_tags=False) == 0
        list_tags.assert_not_called()


def test_check_project_version_cli_help() -> None:
    proc = subprocess.run(
        [sys.executable, str(_DEVTOOLS / "check_project_version.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "--expect" in proc.stdout
    assert "--no-tag-warnings" in proc.stdout
