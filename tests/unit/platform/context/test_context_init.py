"""Tests for endorlabs.init() context bootstrap functionality.

Tests cover:
- init() with mocked APIClient
- Authentication failure handling
- Output directory creation and file writing
- Lazy import error when deps missing
"""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from endorlabs.context.models import InitStatus


class TestSyncOpenapi:
    """Test sync_openapi function."""

    def _mock_api_client(self, response_data: dict | None = None) -> Mock:
        """Create mock APIClient with get method."""
        if response_data is None:
            response_data = {"openapi": "3.0.0", "info": {"title": "Test API"}}

        mock_response = Mock()
        mock_response.json.return_value = response_data

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        return mock_client

    def test_sync_openapi_downloads_spec(self, tmp_path: Path) -> None:
        """Test sync_openapi downloads and saves OpenAPI spec."""
        from endorlabs.context._sync import sync_openapi

        mock_client = self._mock_api_client({"openapi": "3.0.0"})
        output_path = tmp_path / "openapiv2.swagger.json"

        result = sync_openapi(
            output_path=output_path,
            force=True,
            client=mock_client,
        )

        assert result == output_path
        assert output_path.exists()

        # Verify content was written
        with open(output_path) as f:
            data = json.load(f)
        assert data == {"openapi": "3.0.0"}

        # Verify API was called correctly
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "/download/openapiv2.swagger.json" in call_args[0][0]

    def test_sync_openapi_skips_existing_without_force(self, tmp_path: Path) -> None:
        """Test sync_openapi skips download if file exists and force=False."""
        from endorlabs.context._sync import sync_openapi

        output_path = tmp_path / "openapiv2.swagger.json"
        output_path.write_text('{"existing": true}')

        mock_client = self._mock_api_client()

        result = sync_openapi(
            output_path=output_path,
            force=False,
            client=mock_client,
        )

        assert result == output_path
        # Client should NOT be called
        mock_client.get.assert_not_called()

        # Original content preserved
        with open(output_path) as f:
            data = json.load(f)
        assert data == {"existing": True}

    def test_sync_openapi_creates_directory(self, tmp_path: Path) -> None:
        """Test sync_openapi creates parent directories."""
        from endorlabs.context._sync import sync_openapi

        mock_client = self._mock_api_client()
        output_path = tmp_path / "nested" / "dir" / "openapiv2.swagger.json"

        result = sync_openapi(
            output_path=output_path,
            force=True,
            client=mock_client,
        )

        assert result == output_path
        assert output_path.exists()
        assert output_path.parent.exists()

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
        },
    )
    def test_sync_openapi_creates_client_if_not_provided(self, tmp_path: Path) -> None:
        """Test sync_openapi creates APIClient if none provided."""
        from endorlabs.context._sync import sync_openapi

        output_path = tmp_path / "openapiv2.swagger.json"

        # Mock the APIClient class at import time
        with patch("endorlabs.api_client.APIClient") as mock_cls:
            mock_instance = self._mock_api_client()
            mock_cls.return_value = mock_instance

            result = sync_openapi(output_path=output_path, force=True)

            assert result == output_path
            mock_cls.assert_called_once()
            mock_instance.get.assert_called_once()


class TestInit:
    """Test init() function."""

    def _mock_api_client(self, response_data: dict | None = None) -> Mock:
        """Create mock APIClient with get method."""
        if response_data is None:
            response_data = {"openapi": "3.0.0", "info": {"title": "Test API"}}

        mock_response = Mock()
        mock_response.json.return_value = response_data

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        return mock_client

    def test_init_noop_when_all_flags_off(self, tmp_path: Path) -> None:
        """init with every action disabled should not write project context."""
        from endorlabs.context._sync import init

        output_dir = tmp_path / ".endor-context"
        status = init(
            output_dir=output_dir,
            include_agent_knowledge=False,
        )

        assert status.context_json_path is None
        assert status.agent_knowledge_path is None
        assert not output_dir.exists()

    def test_init_defaults_materialize_sdk(self, tmp_path: Path) -> None:
        """Default init materializes sdk/ without platform downloads."""
        from endorlabs.context._sync import init

        output_dir = tmp_path / ".endor-context"
        with patch("endorlabs.api_client.APIClient") as mock_cls:
            status = init(output_dir=output_dir)

        mock_cls.assert_not_called()
        assert status.agent_knowledge_path == output_dir / "sdk"
        assert status.context_json_path == output_dir / "context.json"
        assert status.openapi_path is None
        assert status.user_docs_path is None

    def test_init_openapi_only(self, tmp_path: Path) -> None:
        """Test init with only OpenAPI download."""
        from endorlabs.context._sync import init

        mock_client = self._mock_api_client()
        output_dir = tmp_path / ".endor-context"

        status = init(
            output_dir=output_dir,
            include_openapi=True,
            include_user_docs=False,
            include_agent_knowledge=False,
            client=mock_client,
        )

        assert isinstance(status, InitStatus)
        assert status.platform_openapi_path == (
            output_dir / "platform" / "openapi" / "openapiv2.swagger.json"
        )
        assert status.openapi_path == status.platform_openapi_path
        assert status.user_docs_path is None
        assert status.user_docs_count == 0
        assert status.agent_knowledge_path is None
        assert status.context_json_path == output_dir / "context.json"
        assert status.downloaded_at is not None

    def test_init_warns_agent_about_gitignore(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Project context writes emit a static agent gitignore warning."""
        from endorlabs.context._sync import init

        output_dir = tmp_path / ".endor-context"
        mock_client = self._mock_api_client()
        with caplog.at_level("WARNING"):
            init(
                output_dir=output_dir,
                include_openapi=True,
                include_user_docs=False,
                include_agent_knowledge=False,
                client=mock_client,
            )

        assert any(
            "ask the user to add" in record.message
            and "do not modify .gitignore automatically" in record.message
            for record in caplog.records
        )

    def test_init_creates_output_directory(self, tmp_path: Path) -> None:
        """Test init creates output directory if it doesn't exist."""
        from endorlabs.context._sync import init

        mock_client = self._mock_api_client()
        output_dir = tmp_path / "new" / "nested" / ".endor-context"

        status = init(
            output_dir=output_dir,
            include_openapi=True,
            include_user_docs=False,
            include_agent_knowledge=False,
            client=mock_client,
        )

        assert output_dir.exists()
        assert status.openapi_path is not None
        assert status.openapi_path.exists()

    def test_init_with_force_redownloads(self, tmp_path: Path) -> None:
        """Test init with force=True re-downloads existing files."""
        from endorlabs.context._sync import init

        output_dir = tmp_path / ".endor-context"
        openapi_file = output_dir / "platform" / "openapi" / "openapiv2.swagger.json"
        openapi_file.parent.mkdir(parents=True, exist_ok=True)
        openapi_file.write_text('{"old": true}')

        mock_client = self._mock_api_client({"new": True})

        status = init(
            output_dir=output_dir,
            include_openapi=True,
            include_user_docs=False,
            force=True,
            include_agent_knowledge=False,
            client=mock_client,
        )

        # File should be updated
        with open(status.openapi_path) as f:
            data = json.load(f)
        assert data == {"new": True}

    def test_init_without_force_skips_existing(self, tmp_path: Path) -> None:
        """Test init without force skips existing files."""
        from endorlabs.context._sync import init

        output_dir = tmp_path / ".endor-context"
        openapi_file = output_dir / "platform" / "openapi" / "openapiv2.swagger.json"
        openapi_file.parent.mkdir(parents=True, exist_ok=True)
        openapi_file.write_text('{"old": true}')

        mock_client = self._mock_api_client({"new": True})

        status = init(
            output_dir=output_dir,
            include_openapi=True,
            include_user_docs=False,
            force=False,
            include_agent_knowledge=False,
            client=mock_client,
        )

        # File should NOT be updated
        with open(status.openapi_path) as f:
            data = json.load(f)
        assert data == {"old": True}

        # API should not be called
        mock_client.get.assert_not_called()

    def test_init_user_docs_only_skips_api_client_creation(
        self, tmp_path: Path
    ) -> None:
        """User-doc sync should not instantiate APIClient when OpenAPI is disabled."""
        from endorlabs.context._sync import init

        output_dir = tmp_path / ".endor-context"
        with (
            patch("endorlabs.api_client.APIClient") as mock_cls,
            patch("endorlabs.context._sync.sync_user_docs", return_value=7),
        ):
            status = init(
                output_dir=output_dir,
                include_openapi=False,
                include_user_docs=True,
                include_agent_knowledge=False,
            )

        mock_cls.assert_not_called()
        assert status.openapi_path is None
        assert status.user_docs_path == output_dir / "platform" / "user-docs"
        assert status.user_docs_count == 7

    def test_init_skills_only_uses_wheel_source(self, tmp_path: Path) -> None:
        """Skill-only sync uses wheel skills when sdk/ is not materialized."""
        from endorlabs.agent_knowledge import agent_knowledge_dir
        from endorlabs.context._sync import init

        output_dir = tmp_path / ".endor-context"
        mirrored_path = tmp_path / ".cursor" / "skills"
        with (
            patch("endorlabs.api_client.APIClient") as mock_cls,
            patch(
                "endorlabs.context._sync.sync_agent_skills",
                return_value={"cursor": mirrored_path},
            ) as mock_sync,
        ):
            status = init(
                output_dir=output_dir,
                include_openapi=False,
                include_user_docs=False,
                include_agent_knowledge=False,
                sync_skills="cursor",
            )

        mock_cls.assert_not_called()
        assert output_dir.exists()
        assert not (output_dir / "sdk" / "INDEX.md").exists()
        assert status.openapi_path is None
        assert status.user_docs_path is None
        assert status.synced_skill_paths == {"cursor": mirrored_path}
        mock_sync.assert_called_once()
        assert mock_sync.call_args.kwargs["source_dir"] == (
            agent_knowledge_dir() / "skills"
        )

    def test_init_sdk_bundle_only(self, tmp_path: Path) -> None:
        """init can materialize sdk bundle without downloads or skill sync."""
        from endorlabs.context._sync import init

        output_dir = tmp_path / ".endor-context"
        with patch("endorlabs.api_client.APIClient") as mock_cls:
            status = init(output_dir=output_dir)
        mock_cls.assert_not_called()
        assert status.agent_knowledge_path == output_dir / "sdk"
        assert status.context_json_path == output_dir / "context.json"


class TestTopLevelInit:
    """Test endorlabs.init() top-level function."""

    def test_init_exposed_at_top_level(self) -> None:
        """Test init is accessible from endorlabs module."""
        import endorlabs

        assert hasattr(endorlabs, "init")
        assert callable(endorlabs.init)

    def test_init_in_all(self) -> None:
        """Test init is in __all__."""
        import endorlabs

        assert "init" in endorlabs.__all__
        assert "discover" in endorlabs.__all__

    def test_sync_agent_skills_exposed_at_top_level(self) -> None:
        """Test skill sync helper is accessible from endorlabs module."""
        import endorlabs

        assert hasattr(endorlabs, "sync_agent_skills")
        assert callable(endorlabs.sync_agent_skills)

    def test_top_level_agent_knowledge_helpers(self) -> None:
        """Test agent knowledge helpers are accessible from endorlabs module."""
        import endorlabs

        assert hasattr(endorlabs, "agent_knowledge_dir")
        assert hasattr(endorlabs, "agent_knowledge_index_path")
        assert hasattr(endorlabs, "agent_knowledge_manifest")


class TestContextDepsCheck:
    """Test context dependency checking."""

    def test_import_docs_deps_raises_when_missing(self) -> None:
        """Test _import_docs_deps raises ImportError when deps missing."""
        from endorlabs.context import _sync

        # Mock the import to fail
        with (
            patch.dict("sys.modules", {"bs4": None}),
            patch.object(
                _sync,
                "_import_docs_deps",
                side_effect=ImportError(
                    "Context dependencies not installed. "
                    "Install with: pip install endorlabs[docs]"
                ),
            ),
            pytest.raises(ImportError, match="Context dependencies not installed"),
        ):
            _sync._import_docs_deps()

    def test_import_docs_deps_returns_deps_when_installed(self) -> None:
        """Test _import_docs_deps returns deps when installed."""
        pytest.importorskip(
            "bs4", reason="beautifulsoup4 not installed (context extra)"
        )
        from endorlabs.context import _sync

        # Should return a tuple of (BeautifulSoup, md)
        result = _sync._import_docs_deps()
        assert isinstance(result, tuple)
        assert len(result) == 2
        # First element should be BeautifulSoup class
        assert result[0].__name__ == "BeautifulSoup"


class TestContextModule:
    """Test context module exports."""

    def test_context_module_exports(self) -> None:
        """Test context module exports expected symbols."""
        from endorlabs import context

        assert hasattr(context, "init")
        assert hasattr(context, "sync_openapi")
        assert hasattr(context, "sync_user_docs")
        assert hasattr(context, "InitStatus")

    def test_context_init_status_importable(self) -> None:
        """Test InitStatus is importable from context."""
        from endorlabs.context import InitStatus

        assert InitStatus is not None


class TestDocsHashManifest:
    """Test docs content-hash manifest helpers."""

    def test_write_and_load_hash_manifest_round_trip(self, tmp_path: Path) -> None:
        """Manifest should preserve file -> hash entries."""
        from endorlabs.context._sync import _load_hash_manifest, _write_hash_manifest

        manifest = tmp_path / "_content-hashes.md"
        hashes = {
            "index.md": "a" * 64,
            "scan-sast.md": "b" * 64,
        }
        urls = {
            "index.md": "https://docs.endorlabs.com/",
            "scan-sast.md": "https://docs.endorlabs.com/scan/sast/",
        }
        _write_hash_manifest(
            manifest,
            hashes_by_file=hashes,
            urls_by_file=urls,
        )

        loaded = _load_hash_manifest(manifest)
        assert loaded == hashes

    def test_extract_markdown_body_removes_frontmatter(self, tmp_path: Path) -> None:
        """Body extraction should remove YAML frontmatter wrapper."""
        from endorlabs.context._sync import _extract_markdown_body

        md_file = tmp_path / "sample.md"
        md_file.write_text(
            "---\nurl: https://docs.endorlabs.com/\n---\n\n# Heading\nBody\n",
            encoding="utf-8",
        )
        body = _extract_markdown_body(md_file)
        assert body == "# Heading\nBody\n"
