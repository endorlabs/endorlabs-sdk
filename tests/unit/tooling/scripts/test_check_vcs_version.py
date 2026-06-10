"""Unit tests for devtools/check_vcs_version.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS = _REPO_ROOT / "devtools"
if str(_DEVTOOLS) not in sys.path:
    sys.path.insert(0, str(_DEVTOOLS))

from check_vcs_version import (  # noqa: E402
    check_tag_policy,
    run_check,
)


def test_check_tag_policy_flags_forbidden_dev_tag() -> None:
    issues = check_tag_policy(["v0.1.1.dev19", "v0.2.0.dev0"])
    assert any("v0.1.1.dev19" in issue for issue in issues)
    assert not any("v0.2.0.dev0" in issue for issue in issues)


def test_run_check_expect_match() -> None:
    with patch(
        "check_vcs_version.resolve_hatch_version",
        return_value="0.2.0",
    ):
        assert run_check(expect="0.2.0", release_only=True) == 0


def test_run_check_expect_mismatch() -> None:
    with patch(
        "check_vcs_version.resolve_hatch_version",
        return_value="0.2.0.dev1",
    ):
        assert run_check(expect="0.2.0", release_only=True) == 1


def test_run_check_release_only_skips_tag_scan() -> None:
    with (
        patch("check_vcs_version._list_local_tags") as list_tags,
        patch(
            "check_vcs_version.resolve_hatch_version",
            return_value="0.2.0",
        ),
    ):
        assert run_check(expect="0.2.0", release_only=True) == 0
        list_tags.assert_not_called()


def test_check_vcs_version_cli_help() -> None:
    proc = subprocess.run(
        [sys.executable, str(_DEVTOOLS / "check_vcs_version.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "--expect" in proc.stdout
    assert "--release-only" in proc.stdout
