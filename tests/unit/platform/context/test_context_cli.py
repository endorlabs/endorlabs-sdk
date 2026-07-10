"""Tests for endor-context CLI entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from endorlabs.context import cli as context_cli
from endorlabs.context._project_context import GITIGNORE_ENTRY


def test_parse_args_defaults() -> None:
    """CLI defaults map to init defaults."""
    parsed = context_cli._parse_args([])
    assert parsed.output_dir == ".endorlabs-context"
    assert parsed.include_openapi is False
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
            "--no-materialize-agent-knowledge",
            "--force",
            "--sync-skills",
            "both",
        ]
    )
    assert parsed.output_dir == "tmp-context"
    assert parsed.include_openapi is True
    assert parsed.include_agent_knowledge is False
    assert parsed.force is True
    assert parsed.sync_skills == "both"


def test_print_gitignore_line(capsys: object) -> None:
    """--print-gitignore-line prints entry and exits without init."""
    context_cli.main(["--print-gitignore-line"])
    captured = capsys.readouterr()
    assert captured.out.strip() == GITIGNORE_ENTRY


def test_main_noop_without_actions(monkeypatch: object, capsys: object) -> None:
    """No bootstrap flags should not call init."""
    called = False

    def _fake_init(**kwargs: object) -> object:
        nonlocal called
        called = True
        raise AssertionError("init should not run")

    monkeypatch.setattr("endorlabs.context.cli.endorlabs.init", _fake_init)
    context_cli.main(["--no-materialize-agent-knowledge"])
    assert called is False
    captured = capsys.readouterr()
    assert "No bootstrap actions requested" in captured.out


def test_main_defaults_call_init(monkeypatch: object, tmp_path: Path) -> None:
    """Default main materializes agent knowledge via init."""
    calls: dict[str, object] = {}

    class _Status:
        agent_knowledge_path = tmp_path / "sdk"
        context_json_path = tmp_path / "context.json"
        openapi_path = None
        synced_skill_paths: ClassVar[dict[str, Path]] = {}

    def _fake_init(**kwargs: object) -> _Status:
        calls.update(kwargs)
        return _Status()

    monkeypatch.setattr("endorlabs.context.cli.endorlabs.init", _fake_init)
    context_cli.main(["--output-dir", str(tmp_path)])

    assert calls["output_dir"] == str(tmp_path)
    assert calls["include_openapi"] is False
    assert calls["include_agent_knowledge"] is True
    assert calls["force"] is False
    assert calls["sync_skills"] == "none"


def test_main_calls_endorlabs_init(monkeypatch: object, tmp_path: Path) -> None:
    """Main should delegate argument values into endorlabs.init."""
    calls: dict[str, object] = {}

    class _Status:
        agent_knowledge_path = tmp_path / "sdk"
        context_json_path = tmp_path / "context.json"
        openapi_path = tmp_path / "platform" / "openapi" / "openapiv2.swagger.json"
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
            "--force",
            "--sync-skills",
            "cursor",
        ]
    )

    assert calls["output_dir"] == str(tmp_path)
    assert calls["include_openapi"] is True
    assert calls["include_agent_knowledge"] is True
    assert calls["force"] is True
    assert calls["sync_skills"] == "cursor"
