"""Tests for endor-context CLI entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    import pytest

from endorlabs.context import cli as context_cli
from endorlabs.context._project_context import GITIGNORE_ENTRY


def test_parse_args_defaults() -> None:
    """CLI defaults map to init defaults."""
    parsed = context_cli._parse_args([])
    assert parsed.output_dir == ".endorlabs-context"
    assert parsed.include_openapi is False
    assert parsed.include_user_docs is False
    assert parsed.max_pages is None
    assert parsed.force is False
    assert parsed.sync_skills == "none"
    assert parsed.include_agent_knowledge is True


def test_parse_args_supports_switches() -> None:
    """CLI supports explicit bootstrap flags."""
    parsed = context_cli._parse_args(
        [
            "--output-dir",
            "tmp-context",
            "--sync-openapi",
            "--sync-user-docs",
            "--no-materialize-agent-knowledge",
            "--max-pages",
            "12",
            "--force",
            "--sync-skills",
            "both",
        ]
    )
    assert parsed.output_dir == "tmp-context"
    assert parsed.include_openapi is True
    assert parsed.include_user_docs is True
    assert parsed.include_agent_knowledge is False
    assert parsed.max_pages == 12
    assert parsed.force is True
    assert parsed.sync_skills == "both"


def test_print_gitignore_line(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI can print the recommended gitignore entry."""
    context_cli.main(["--print-gitignore-line"])
    captured = capsys.readouterr()
    assert captured.out.strip() == GITIGNORE_ENTRY.rstrip("/") + "/"


def test_main_noop_without_actions(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Main should not call init when every action is disabled."""
    called = {"init": False}

    def _fake_init(**kwargs: object) -> None:
        called["init"] = True

    monkeypatch.setattr("endorlabs.context.cli.endorlabs.init", _fake_init)
    context_cli.main(["--no-materialize-agent-knowledge"])
    assert called["init"] is False
    captured = capsys.readouterr()
    assert "No bootstrap actions requested" in captured.out


def test_main_defaults_call_init(monkeypatch: object, tmp_path: Path) -> None:
    """Bare CLI invocation materializes agent knowledge by default."""
    calls: dict[str, object] = {}

    class _Status:
        agent_knowledge_path = tmp_path / "sdk"
        context_json_path = tmp_path / "context.json"
        openapi_path = None
        user_docs_path = None
        user_docs_count = 0
        synced_skill_paths: ClassVar[dict[str, Path]] = {}

    def _fake_init(**kwargs: object) -> _Status:
        calls.update(kwargs)
        return _Status()

    monkeypatch.setattr("endorlabs.context.cli.endorlabs.init", _fake_init)
    context_cli.main(["--output-dir", str(tmp_path)])

    assert calls["output_dir"] == str(tmp_path)
    assert calls["include_agent_knowledge"] is True
    assert calls["include_openapi"] is False
    assert calls["include_user_docs"] is False


def test_main_calls_endorlabs_init(monkeypatch: object, tmp_path: Path) -> None:
    """Main should delegate argument values into endorlabs.init."""
    calls: dict[str, object] = {}

    class _Status:
        agent_knowledge_path = tmp_path / "sdk"
        context_json_path = tmp_path / "context.json"
        openapi_path = tmp_path / "platform" / "openapi" / "openapiv2.swagger.json"
        user_docs_path = tmp_path / "platform" / "user-docs"
        user_docs_count = 42
        synced_skill_paths: ClassVar[dict[str, Path]] = {}

    def _fake_init(**kwargs: object) -> _Status:
        calls.update(kwargs)
        return _Status()

    monkeypatch.setattr("endorlabs.context.cli.endorlabs.init", _fake_init)
    context_cli.main(
        [
            "--output-dir",
            str(tmp_path),
            "--sync-openapi",
            "--sync-user-docs",
            "--max-pages",
            "5",
            "--force",
            "--sync-skills",
            "cursor",
        ]
    )

    assert calls["output_dir"] == str(tmp_path)
    assert calls["include_openapi"] is True
    assert calls["include_user_docs"] is True
    assert calls["include_agent_knowledge"] is True
    assert calls["max_pages"] == 5
    assert calls["force"] is True
    assert calls["sync_skills"] == "cursor"
