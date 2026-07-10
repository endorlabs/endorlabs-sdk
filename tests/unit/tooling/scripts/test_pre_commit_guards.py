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
    check_accessor_nudge,
    check_agent_knowledge_sync,
    check_blocked_staged_paths,
    check_bounds_shim,
    check_changelog_reminder,
    check_context_root_literals,
    check_deprecated_api_strings,
    check_layer_imports,
    check_portable_examples,
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


def test_check_layer_imports_allows_estate_internal(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "pre_commit_guards._REPO_ROOT",
        tmp_path,
    )
    estate_file = (
        tmp_path / "src" / "endorlabs" / "workflows" / "estate" / "collect" / "x.py"
    )
    estate_file.parent.mkdir(parents=True)
    estate_file.write_text(
        "from endorlabs.workflows.estate.collect.runner import collect_workspace\n",
        encoding="utf-8",
    )
    assert (
        check_layer_imports(
            paths=["src/endorlabs/workflows/estate/collect/x.py"],
        )
        == 0
    )


def test_check_layer_imports_blocks_non_estate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    bad = tmp_path / "src" / "endorlabs" / "workflows" / "semgrep" / "inventory.py"
    bad.parent.mkdir(parents=True)
    bad.write_text(
        "from endorlabs.workflows.estate.collect.bounds import resolve_max_pages\n",
        encoding="utf-8",
    )
    assert (
        check_layer_imports(paths=["src/endorlabs/workflows/semgrep/inventory.py"]) == 1
    )


def test_check_bounds_shim_blocks_import(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    bad = tmp_path / "src" / "endorlabs" / "workflows" / "semgrep" / "inventory.py"
    bad.parent.mkdir(parents=True)
    bad.write_text(
        "from endorlabs.workflows.estate.collect.bounds import resolve_max_pages\n",
        encoding="utf-8",
    )
    assert (
        check_bounds_shim(paths=["src/endorlabs/workflows/semgrep/inventory.py"]) == 1
    )


def test_check_bounds_shim_allows_tools(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    ok = tmp_path / "src" / "endorlabs" / "workflows" / "semgrep" / "inventory.py"
    ok.parent.mkdir(parents=True)
    ok.write_text(
        "from endorlabs.tools.list_bounds import resolve_max_pages\n",
        encoding="utf-8",
    )
    assert (
        check_bounds_shim(paths=["src/endorlabs/workflows/semgrep/inventory.py"]) == 0
    )


def test_check_deprecated_api_strings_blocks(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    doc = tmp_path / "docs" / "guides" / "examples.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("project = client.Project.resolve(uuid=...)\n", encoding="utf-8")
    assert check_deprecated_api_strings(paths=["docs/guides/examples.md"]) == 1


def test_check_deprecated_api_strings_allows_removed_note(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    doc = tmp_path / "docs" / "guides" / "facade-helpers.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "**Removed (0.3.0):** `Project.resolve()` — see changelog.\n",
        encoding="utf-8",
    )
    assert check_deprecated_api_strings(paths=["docs/guides/facade-helpers.md"]) == 0


def test_check_deprecated_api_strings_skips_changelog(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    doc = tmp_path / "docs" / "changelog.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("Removed Project.resolve().\n", encoding="utf-8")
    assert check_deprecated_api_strings(paths=["docs/changelog.md"]) == 0


def test_check_accessor_nudge_warns(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    wf = tmp_path / "src" / "endorlabs" / "workflows" / "findings" / "x.py"
    wf.parent.mkdir(parents=True)
    wf.write_text(
        "from endorlabs import Client\nfilt = f'spec.project_uuid==\"{uuid}\"'\n",
        encoding="utf-8",
    )
    assert check_accessor_nudge(paths=["src/endorlabs/workflows/findings/x.py"]) == 0
    assert "warning:" in capsys.readouterr().err


def test_check_layer_imports_blocks_tools_to_workflows(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    bad = tmp_path / "src" / "endorlabs" / "tools" / "x.py"
    bad.parent.mkdir(parents=True)
    bad.write_text(
        "from endorlabs.workflows.common import WorkflowResult\n",
        encoding="utf-8",
    )
    assert check_layer_imports(paths=["src/endorlabs/tools/x.py"]) == 1


def test_check_layer_imports_allows_callgraph_render_shim(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    ok = tmp_path / "src" / "endorlabs" / "tools" / "callgraph_artifacts.py"
    ok.parent.mkdir(parents=True)
    ok.write_text(
        "from endorlabs.workflows.callgraph.render import render_callgraph_analysis\n",
        encoding="utf-8",
    )
    assert (
        check_layer_imports(paths=["src/endorlabs/tools/callgraph_artifacts.py"]) == 0
    )


def test_check_layer_imports_blocks_devtools(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    bad = tmp_path / "src" / "endorlabs" / "client.py"
    bad.parent.mkdir(parents=True)
    bad.write_text("import devtools.git_staged\n", encoding="utf-8")
    assert check_layer_imports(paths=["src/endorlabs/client.py"]) == 1


def test_check_portable_examples_warns(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    doc = tmp_path / "docs" / "guides" / "examples.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "uuid = 69458a5fd899e9af5f6e0f4f\n",
        encoding="utf-8",
    )
    assert check_portable_examples(paths=["docs/guides/examples.md"]) == 0
    assert "warning:" in capsys.readouterr().err


def test_check_agent_knowledge_sync_reminds(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    assert (
        check_agent_knowledge_sync(
            paths=["agent-knowledge/rules/endor-foo.md"],
        )
        == 0
    )
    assert "reminder:" in capsys.readouterr().err


def test_check_agent_knowledge_sync_silent_when_shipped(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    assert (
        check_agent_knowledge_sync(
            paths=[
                "agent-knowledge/rules/endor-foo.md",
                "src/endorlabs/agent_knowledge/rules/endor-foo.md",
            ],
        )
        == 0
    )
    assert capsys.readouterr().err == ""


def test_check_context_root_literals_blocks(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    bad = tmp_path / "src" / "endorlabs" / "workflows" / "foo.py"
    bad.parent.mkdir(parents=True)
    bad.write_text(
        'from pathlib import Path\nroot = Path(".endorlabs-context")\n',
        encoding="utf-8",
    )
    assert check_context_root_literals(paths=["src/endorlabs/workflows/foo.py"]) == 1


def test_check_context_root_literals_allows_paths_module(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    ok = tmp_path / "src" / "endorlabs" / "context" / "paths.py"
    ok.parent.mkdir(parents=True)
    ok.write_text('DEFAULT_CONTEXT_DIR = ".endorlabs-context"\n', encoding="utf-8")
    assert check_context_root_literals(paths=["src/endorlabs/context/paths.py"]) == 0


def test_check_context_root_literals_allows_prose_mention(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    ok = tmp_path / "src" / "endorlabs" / "workflows" / "foo.py"
    ok.parent.mkdir(parents=True)
    ok.write_text(
        '"""Write under .endorlabs-context/workspace/ after init."""\n',
        encoding="utf-8",
    )
    assert check_context_root_literals(paths=["src/endorlabs/workflows/foo.py"]) == 0


def test_check_context_root_literals_scans_skill_scripts(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("pre_commit_guards._REPO_ROOT", tmp_path)
    bad = (
        tmp_path / "agent-knowledge" / "skills" / "endor-foo" / "scripts" / "report.py"
    )
    bad.parent.mkdir(parents=True)
    bad.write_text('OUT = ".endorlabs-context/workspace/runs/foo"\n', encoding="utf-8")
    assert (
        check_context_root_literals(
            paths=["agent-knowledge/skills/endor-foo/scripts/report.py"],
        )
        == 1
    )
