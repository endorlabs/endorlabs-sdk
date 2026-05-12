"""Unit tests for the maintainer refresh helper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from endorlabs.context import _maintainer_refresh


def test_main_refreshes_skill_mirrors_for_skills_changes(monkeypatch: object) -> None:
    """Skill-source changes should invoke runtime skill mirroring."""
    sync_mock = Mock(return_value={"cursor": Path(".cursor/skills")})
    init_mock = Mock()

    monkeypatch.setattr(_maintainer_refresh.endorlabs, "sync_agent_skills", sync_mock)
    monkeypatch.setattr(_maintainer_refresh.endorlabs, "init", init_mock)

    result = _maintainer_refresh.main(["skills-src/README.md"])

    assert result == 0
    sync_mock.assert_called_once_with(
        repo_root=_maintainer_refresh.REPO_ROOT,
        target="auto",
    )
    init_mock.assert_not_called()


def test_main_skips_context_refresh_when_context_dir_missing(
    tmp_path: Path, monkeypatch: object
) -> None:
    """Context refresh should no-op when no local context download exists."""
    init_mock = Mock()

    monkeypatch.setattr(
        _maintainer_refresh, "CONTEXT_DIR", tmp_path / ".endorlabs-context"
    )
    monkeypatch.setattr(_maintainer_refresh.endorlabs, "init", init_mock)

    result = _maintainer_refresh.main(["src/endorlabs/context/_sync.py"])

    assert result == 0
    init_mock.assert_not_called()


def test_main_refreshes_context_without_openapi_when_auth_missing(
    tmp_path: Path, monkeypatch: object
) -> None:
    """Context refresh should skip OpenAPI when auth is unavailable."""
    context_dir = tmp_path / ".endorlabs-context"
    context_dir.mkdir()
    status = Mock(
        user_docs_path=context_dir / "docs", user_docs_count=12, openapi_path=None
    )
    init_mock = Mock(return_value=status)

    monkeypatch.setattr(_maintainer_refresh, "CONTEXT_DIR", context_dir)
    monkeypatch.setattr(_maintainer_refresh.endorlabs, "init", init_mock)
    monkeypatch.delenv("ENDOR_TOKEN", raising=False)
    monkeypatch.delenv("ENDOR_API_CREDENTIALS_KEY", raising=False)
    monkeypatch.delenv("ENDOR_API_CREDENTIALS_SECRET", raising=False)

    result = _maintainer_refresh.main(["src/endorlabs/context/_sync.py"])

    assert result == 0
    init_mock.assert_called_once_with(
        output_dir=context_dir,
        include_openapi=False,
        include_user_docs=True,
        force=True,
        sync_skills="none",
    )
