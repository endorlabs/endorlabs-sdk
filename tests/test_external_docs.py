"""
Tests for external documentation downloads.

Tests the functionality of downloading and processing external documentation
including OpenAPI spec, sitemap.xml, and user documentation pages.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
import requests

from holocron.external_docs import (
    check_download_freshness,
    download_openapi_spec,
    download_sitemap,
    download_user_docs,
    sanitize_filename,
)


class TestSanitizeFilename:
    """Test URL to filename conversion."""

    def test_basic_url(self):
        """Test basic URL sanitization."""
        url = "https://docs.endorlabs.com/getting-started/introduction"
        result = sanitize_filename(url)
        assert result == "getting-started-introduction.md"

    def test_url_with_special_chars(self):
        """Test URL with special characters."""
        url = "https://docs.endorlabs.com/api/v1/projects#details"
        result = sanitize_filename(url)
        # URL fragments are not included in the path
        assert result == "api-v1-projects.md"

    def test_url_with_query_params(self):
        """Test URL with query parameters (should be stripped)."""
        url = "https://docs.endorlabs.com/guide?tab=1&section=intro"
        result = sanitize_filename(url)
        assert result.endswith(".md")
        assert "guide" in result


class TestDownloadOpenAPISpec:
    """Test OpenAPI specification download."""

    @patch("holocron.external_docs.requests.get")
    def test_successful_download(self, mock_get, tmp_path):
        """Test successful OpenAPI spec download."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "swagger": "2.0",
            "info": {"title": "Endor API", "version": "1.0.0"},
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Download to temp path
        output_path = tmp_path / "openapi.json"
        result = download_openapi_spec(
            "https://api.endorlabs.com", output_path
        )

        # Verify metadata
        assert "file_hash" in result
        assert "timestamp" in result
        assert "size" in result
        assert "url" in result

        # Verify file exists
        assert output_path.exists()

    @patch("holocron.external_docs.requests.get")
    def test_retry_on_failure(self, mock_get, tmp_path):
        """Test retry logic on request failure."""
        # First two calls fail, third succeeds
        mock_response = Mock()
        mock_response.json.return_value = {"swagger": "2.0"}
        mock_response.raise_for_status = Mock()

        mock_get.side_effect = [
            requests.exceptions.RequestException("Timeout"),
            requests.exceptions.RequestException("Timeout"),
            mock_response,
        ]

        output_path = tmp_path / "openapi.json"
        result = download_openapi_spec(
            "https://api.endorlabs.com", output_path, timeout=1
        )

        # Should succeed after retries
        assert result is not None
        assert mock_get.call_count == 3


class TestDownloadSitemap:
    """Test sitemap.xml download and parsing."""

    @patch("holocron.external_docs.requests.get")
    def test_sitemap_parsing(self, mock_get, tmp_path):
        """Test sitemap XML parsing."""
        # Mock sitemap XML
        sitemap_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://docs.endorlabs.com/page1</loc>
    </url>
    <url>
        <loc>https://docs.endorlabs.com/page2</loc>
    </url>
</urlset>"""

        mock_response = Mock()
        mock_response.content = sitemap_xml
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Download and parse
        output_path = tmp_path / "sitemap.xml"
        urls = download_sitemap("https://docs.endorlabs.com/sitemap.xml", output_path)

        # Verify URLs extracted
        assert len(urls) == 2
        assert "https://docs.endorlabs.com/page1" in urls
        assert "https://docs.endorlabs.com/page2" in urls


class TestDownloadUserDocs:
    """Test user documentation download."""

    @patch("holocron.external_docs.requests.get")
    def test_download_with_limit(self, mock_get, tmp_path):
        """Test downloading with max_pages limit."""
        # Mock HTML response
        mock_response = Mock()
        mock_response.content = b"<main><h1>Test Page</h1><p>Content</p></main>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Download with limit
        urls = [
            "https://docs.endorlabs.com/page1",
            "https://docs.endorlabs.com/page2",
            "https://docs.endorlabs.com/page3",
        ]
        output_dir = tmp_path / "docs"

        count = download_user_docs(urls, output_dir, max_pages=2)

        # Should only download 2 pages
        assert count == 2
        assert mock_get.call_count == 2

    @patch("holocron.external_docs.requests.get")
    def test_handle_failed_download(self, mock_get, tmp_path):
        """Test graceful handling of failed page downloads."""
        # First page succeeds, second fails
        success_response = Mock()
        success_response.content = b"<main><h1>Test</h1></main>"
        success_response.raise_for_status = Mock()

        mock_get.side_effect = [
            success_response,
            requests.exceptions.RequestException("Failed"),
        ]

        urls = [
            "https://docs.endorlabs.com/page1",
            "https://docs.endorlabs.com/page2",
        ]
        output_dir = tmp_path / "docs"

        count = download_user_docs(urls, output_dir)

        # Should succeed with 1 page despite failure
        assert count == 1


class TestCheckDownloadFreshness:
    """Test download freshness checking."""

    def test_fresh_downloads(self, tmp_path):
        """Test with fresh downloads (<7 days old)."""
        manifest_path = tmp_path / "manifest.json"

        # Create manifest with fresh timestamps
        manifest = {
            "external_docs": {
                "openapi_spec": {"last_downloaded": datetime.now().isoformat()},
                "user_docs": {"last_downloaded": datetime.now().isoformat()},
            }
        }

        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        needs_refresh, ages = check_download_freshness(manifest_path)

        assert not needs_refresh
        assert ages["openapi_spec"] == 0
        assert ages["user_docs"] == 0

    def test_stale_downloads(self, tmp_path):
        """Test with stale downloads (>7 days old)."""
        manifest_path = tmp_path / "manifest.json"

        # Create manifest with old timestamps (10 days ago)
        from datetime import timedelta

        old_date = datetime.now() - timedelta(days=10)
        manifest = {
            "external_docs": {
                "openapi_spec": {"last_downloaded": old_date.isoformat()},
                "user_docs": {"last_downloaded": old_date.isoformat()},
            }
        }

        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        needs_refresh, ages = check_download_freshness(manifest_path)

        assert needs_refresh
        assert ages["openapi_spec"] == 10
        assert ages["user_docs"] == 10

    def test_missing_manifest(self, tmp_path):
        """Test with non-existent manifest file."""
        manifest_path = tmp_path / "nonexistent.json"

        needs_refresh, ages = check_download_freshness(manifest_path)

        assert needs_refresh
        assert ages == {}

