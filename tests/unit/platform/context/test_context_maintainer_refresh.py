"""Unit tests for the maintainer refresh helper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from endorlabs.context import _maintainer_refresh


def test_main_refreshes_skill_mirrors_for_skills_changes(monkeypatch: object) -> None:
    """Skill-source changes should regenerate bundle and invoke runtime mirroring."""
    sync_mock = Mock(return_value={"cursor": Path(".cursor/skills")})
    init_mock = Mock()
    bundle_sync_mock = Mock()

    monkeypatch.setattr(
        _maintainer_refresh, "_configured_skill_sync_target", lambda: "cursor"
    )
    monkeypatch.setattr(_maintainer_refresh, "_run_bundle_sync", bundle_sync_mock)
    monkeypatch.setattr(_maintainer_refresh.endorlabs, "sync_agent_skills", sync_mock)
    monkeypatch.setattr(_maintainer_refresh.endorlabs, "init", init_mock)

    result = _maintainer_refresh.main(["agent-skills/README.md"])

    assert result == 0
    bundle_sync_mock.assert_called_once()
    sync_mock.assert_called_once_with(
        repo_root=_maintainer_refresh.REPO_ROOT,
        target="cursor",
        source_dir=_maintainer_refresh.REPO_ROOT / "agent-skills",
    )
    init_mock.assert_not_called()


def test_main_skips_skill_sync_when_no_runtime_mirror_is_configured(
    monkeypatch: object,
) -> None:
    """Skill-source changes should no-op when no host mirror is configured."""
    sync_mock = Mock()

    monkeypatch.setattr(
        _maintainer_refresh, "_configured_skill_sync_target", lambda: None
    )
    monkeypatch.setattr(_maintainer_refresh.endorlabs, "sync_agent_skills", sync_mock)

    result = _maintainer_refresh.main(["agent-skills/README.md"])

    assert result == 0
    sync_mock.assert_not_called()


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
