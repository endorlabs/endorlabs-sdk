"""Unit tests for devtools/verify_ship_artifacts.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS = _REPO_ROOT / "devtools"
if str(_DEVTOOLS) not in sys.path:
    sys.path.insert(0, str(_DEVTOOLS))

from verify_ship_artifacts import (  # noqa: E402
    changelog_has_version,
    run_verify,
    ship_git_paths,
    verify_changelog_version,
)


def _ok_process() -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")


def test_ship_git_paths_includes_core_artifacts() -> None:
    paths = ship_git_paths()
    assert "src/endorlabs/generated/registry_contract.py" in paths
    assert "src/endorlabs/generated/route_contract.py" in paths
    assert "src/endorlabs/client_surface.pyi" in paths
    assert "docs/generated-reference/resources.md" in paths
    assert "docs/generated-reference/resource-routes.md" in paths
    assert "docs/generated-reference/filter-enum-snippets.md" in paths


def test_changelog_has_version_matches_section() -> None:
    text = "## Unreleased\n\n### Added\n\n- foo\n\n## 1.2.3\n\n### Changed\n\n- bar\n"
    assert changelog_has_version(text, "1.2.3")
    assert not changelog_has_version(text, "9.9.9")


def test_verify_changelog_version_missing(tmp_path: Path) -> None:
    changelog = tmp_path / "docs" / "changelog.md"
    changelog.parent.mkdir(parents=True)
    changelog.write_text("## Unreleased\n", encoding="utf-8")
    err = verify_changelog_version("0.1.0", root=tmp_path)
    assert err is not None
    assert "0.1.0" in err


def test_verify_changelog_version_present(tmp_path: Path) -> None:
    changelog = tmp_path / "docs" / "changelog.md"
    changelog.parent.mkdir(parents=True)
    changelog.write_text("## 0.1.0\n\n### Added\n", encoding="utf-8")
    assert verify_changelog_version("0.1.0", root=tmp_path) is None


def test_git_diff_dirty_clean_repo() -> None:
    from verify_ship_artifacts import git_diff_dirty

    err = git_diff_dirty(ship_git_paths(), root=_REPO_ROOT)
    assert err is None


def test_git_diff_dirty_reports_when_diff_nonzero() -> None:
    from verify_ship_artifacts import git_diff_dirty

    def fake_run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        if cmd[:3] == ["git", "diff", "--exit-code"]:
            return subprocess.CompletedProcess(
                args=cmd, returncode=1, stdout="", stderr=""
            )
        if cmd[:3] == ["git", "diff", "--stat"]:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=" src/endorlabs/generated/registry_contract.py | 2 +-\n",
                stderr="",
            )
        raise AssertionError(f"unexpected cmd: {cmd}")

    with patch("verify_ship_artifacts._run", side_effect=fake_run):
        err = git_diff_dirty(
            ("src/endorlabs/generated/registry_contract.py",),
            root=_REPO_ROOT,
        )

    assert err is not None
    assert "out of date" in err
    assert "registry_contract.py" in err


def _write_skip_upstream_fixtures(root: Path) -> None:
    spec = root / ".endorlabs-context/platform/openapi/openapiv2.swagger.json"
    spec.parent.mkdir(parents=True)
    spec.write_text("{}", encoding="utf-8")
    regen = root / "src/endorlabs/generated/registry_contract.py"
    regen.parent.mkdir(parents=True)
    regen.write_text("# ok", encoding="utf-8")
    models_init = root / "src/endorlabs/generated/models/__init__.py"
    models_init.parent.mkdir(parents=True, exist_ok=True)
    models_init.write_text("", encoding="utf-8")


def test_run_verify_skip_upstream_skips_upstream_only(tmp_path: Path) -> None:
    _write_skip_upstream_fixtures(tmp_path)

    def _mentions(cmd: list[str], needle: str) -> bool:
        return any(needle in part for part in cmd)

    def fake_run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        if _mentions(cmd, "model_sync.py") and "--verify-upstream-only" in cmd:
            raise AssertionError("upstream verify should be skipped")
        if _mentions(cmd, "model_sync.py"):
            return _ok_process()
        if _mentions(cmd, "generate_route_contract.py"):
            return _ok_process()
        if _mentions(cmd, "generate_filter_enum_reference.py"):
            return _ok_process()
        if _mentions(cmd, "sync_agent_knowledge.py"):
            return _ok_process()
        if cmd[:3] == ["git", "diff", "--exit-code"]:
            return _ok_process()
        if cmd[:3] == ["git", "diff", "--stat"]:
            return _ok_process()
        raise AssertionError(f"unexpected cmd: {cmd}")

    with patch("verify_ship_artifacts._run", side_effect=fake_run):
        assert run_verify(skip_upstream=True, root=tmp_path) == 0
