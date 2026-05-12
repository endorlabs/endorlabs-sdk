"""Tests for endor-context CLI entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from endorlabs.context import cli as context_cli


def test_parse_args_defaults() -> None:
    """CLI defaults map to endorlabs.init defaults."""
    parsed = context_cli._parse_args([])
    assert parsed.output_dir == ".endorlabs-context"
    assert parsed.include_openapi is True
    assert parsed.include_user_docs is True
    assert parsed.max_pages is None
    assert parsed.force is False
    assert parsed.sync_skills == "none"


def test_parse_args_supports_switches() -> None:
    """CLI supports toggling openapi/docs and force mode."""
    parsed = context_cli._parse_args(
        [
            "--output-dir",
            "tmp-context",
            "--no-openapi",
            "--no-user-docs",
            "--max-pages",
            "12",
            "--force",
            "--sync-skills",
            "auto",
        ]
    )
    assert parsed.output_dir == "tmp-context"
    assert parsed.include_openapi is False
    assert parsed.include_user_docs is False
    assert parsed.max_pages == 12
    assert parsed.force is True
    assert parsed.sync_skills == "auto"


def test_main_calls_endorlabs_init(monkeypatch: object, tmp_path: Path) -> None:
    """Main should delegate argument values into endorlabs.init."""
    calls: dict[str, object] = {}

    class _Status:
        openapi_path = tmp_path / "openapiv2.swagger.json"
        user_docs_path = tmp_path / "docs"
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
    assert calls["max_pages"] == 5
    assert calls["force"] is True
    assert calls["sync_skills"] == "cursor"
