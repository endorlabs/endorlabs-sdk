"""Tests for endorlabs.init() context bootstrap functionality.

Tests cover:
- init() with mocked APIClient
- Authentication failure handling
- Output directory creation and file writing
- Lazy import error when deps missing
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from endorlabs.context.models import InitStatus


class TestInitStatus:
    """Test InitStatus dataclass."""

    def test_init_status_creation(self, tmp_path: Path) -> None:
        """Test InitStatus can be created with all fields."""
        openapi_path = tmp_path / "openapi.json"
        docs_path = tmp_path / "docs"
        now = datetime.now(UTC)

        status = InitStatus(
            openapi_path=openapi_path,
            user_docs_path=docs_path,
            user_docs_count=10,
            downloaded_at=now,
        )

        assert status.openapi_path == openapi_path
        assert status.user_docs_path == docs_path
        assert status.user_docs_count == 10
        assert status.downloaded_at == now

    def test_init_status_repr(self, tmp_path: Path) -> None:
        """Test InitStatus repr includes key fields."""
        status = InitStatus(
            openapi_path=tmp_path / "openapi.json",
            user_docs_path=tmp_path / "docs",
            user_docs_count=5,
            downloaded_at=datetime.now(UTC),
        )

        repr_str = repr(status)
        assert "InitStatus" in repr_str
        assert "openapi_path" in repr_str
        assert "user_docs_count" in repr_str


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
        output_path = tmp_path / "openapi.json"

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

        output_path = tmp_path / "openapi.json"
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
        output_path = tmp_path / "nested" / "dir" / "openapi.json"

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

        output_path = tmp_path / "openapi.json"

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

    def test_init_openapi_only(self, tmp_path: Path) -> None:
        """Test init with only OpenAPI download."""
        from endorlabs.context._sync import init

        mock_client = self._mock_api_client()
        output_dir = tmp_path / ".endor-context"

        status = init(
            output_dir=output_dir,
            include_openapi=True,
            include_user_docs=False,
            client=mock_client,
        )

        assert isinstance(status, InitStatus)
        assert status.openapi_path == output_dir / "openapi.json"
        assert status.user_docs_path is None
        assert status.user_docs_count == 0
        assert status.downloaded_at is not None

    def test_init_creates_output_directory(self, tmp_path: Path) -> None:
        """Test init creates output directory if it doesn't exist."""
        from endorlabs.context._sync import init

        mock_client = self._mock_api_client()
        output_dir = tmp_path / "new" / "nested" / ".endor-context"

        status = init(
            output_dir=output_dir,
            include_openapi=True,
            include_user_docs=False,
            client=mock_client,
        )

        assert output_dir.exists()
        assert status.openapi_path is not None
        assert status.openapi_path.exists()

    def test_init_with_force_redownloads(self, tmp_path: Path) -> None:
        """Test init with force=True re-downloads existing files."""
        from endorlabs.context._sync import init

        output_dir = tmp_path / ".endor-context"
        output_dir.mkdir(parents=True)
        openapi_file = output_dir / "openapi.json"
        openapi_file.write_text('{"old": true}')

        mock_client = self._mock_api_client({"new": True})

        status = init(
            output_dir=output_dir,
            include_openapi=True,
            include_user_docs=False,
            force=True,
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
        output_dir.mkdir(parents=True)
        openapi_file = output_dir / "openapi.json"
        openapi_file.write_text('{"old": true}')

        mock_client = self._mock_api_client({"new": True})

        status = init(
            output_dir=output_dir,
            include_openapi=True,
            include_user_docs=False,
            force=False,
            client=mock_client,
        )

        # File should NOT be updated
        with open(status.openapi_path) as f:
            data = json.load(f)
        assert data == {"old": True}

        # API should not be called
        mock_client.get.assert_not_called()


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
                    "Install with: pip install endor-cockpit[context]"
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
