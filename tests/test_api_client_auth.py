"""Tests for APIClient authentication with token expiration tracking.

Browser auth tests are marked @pytest.mark.local so CI runs
`pytest -m \"integration and not local\"` and excludes them; run with mocks locally.
"""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from endor_cockpit.api_client import APIClient


class TestTokenExpirationTracking:
    """Test token expiration tracking and proactive refresh."""

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",  # Clear any stored token
            "ENDOR_AUTH_METHOD": "",  # Clear auth method
        },
        clear=True,
    )
    @patch("endor_cockpit.api_client.requests.post")
    def test_token_expiration_parsing(self, mock_post) -> None:
        """Test that token expiration is parsed from API response."""
        # Mock response with expiration
        future_time = datetime.now(UTC) + timedelta(hours=1)
        expiration_str = future_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        mock_response = Mock()
        mock_response.json.return_value = {
            "token": "test-token",
            "expirationTime": expiration_str,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = APIClient()

        assert client._token == "test-token"
        assert client._token_expires is not None
        # Allow small time difference
        assert abs((client._token_expires - future_time).total_seconds()) < 1

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
            "ENDOR_AUTH_METHOD": "",
        },
        clear=True,
    )
    @patch("endor_cockpit.api_client.requests.post")
    def test_token_expiration_alternative_field(self, mock_post) -> None:
        """Test parsing expiration_time field (alternative to expirationTime)."""
        future_time = datetime.now(UTC) + timedelta(hours=1)
        expiration_str = future_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        mock_response = Mock()
        mock_response.json.return_value = {
            "token": "test-token",
            "expiration_time": expiration_str,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = APIClient()

        assert client._token_expires is not None
        assert abs((client._token_expires - future_time).total_seconds()) < 1

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
            "ENDOR_AUTH_METHOD": "",
        },
        clear=True,
    )
    @patch("endor_cockpit.api_client.requests.post")
    def test_token_property_refresh(self, mock_post) -> None:
        """Test token property triggers refresh when expired."""
        # First authentication
        future_time = datetime.now(UTC) + timedelta(minutes=10)
        expiration_str = future_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        mock_response1 = Mock()
        mock_response1.json.return_value = {
            "token": "initial-token",
            "expirationTime": expiration_str,
        }
        mock_response1.raise_for_status = Mock()

        # Second authentication (refresh)
        new_future_time = datetime.now(UTC) + timedelta(hours=1)
        new_expiration_str = new_future_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        mock_response2 = Mock()
        mock_response2.json.return_value = {
            "token": "refreshed-token",
            "expirationTime": new_expiration_str,
        }
        mock_response2.raise_for_status = Mock()

        mock_post.side_effect = [mock_response1, mock_response2]

        client = APIClient()

        # Manually set expiration to past to trigger refresh
        client._token_expires = datetime.now(UTC) - timedelta(hours=1)

        # Access token property should trigger refresh
        token = client.token

        assert token == "refreshed-token"
        assert mock_post.call_count == 2

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
            "ENDOR_AUTH_METHOD": "",
        },
        clear=True,
    )
    @patch("endor_cockpit.api_client.requests.post")
    def test_is_expired_property(self, mock_post) -> None:
        """Test is_expired property correctly identifies expired tokens."""
        future_time = datetime.now(UTC) + timedelta(hours=1)
        expiration_str = future_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        mock_response = Mock()
        mock_response.json.return_value = {
            "token": "test-token",
            "expirationTime": expiration_str,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = APIClient()

        # Token not expired
        assert client.is_expired is False

        # Set expiration to past
        client._token_expires = datetime.now(UTC) - timedelta(minutes=2)
        assert client.is_expired is True

        # Set expiration to near future (within 60 seconds)
        client._token_expires = datetime.now(UTC) + timedelta(seconds=30)
        assert client.is_expired is True

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
            "ENDOR_AUTH_METHOD": "",
        },
        clear=True,
    )
    @patch("endor_cockpit.api_client.requests.post")
    def test_proactive_refresh_30_minutes(self, mock_post) -> None:
        """Test proactive refresh triggers 30 minutes before expiration."""
        # Set expiration to 25 minutes from now (within 30-minute buffer)
        near_future = datetime.now(UTC) + timedelta(minutes=25)
        expiration_str = near_future.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        mock_response1 = Mock()
        mock_response1.json.return_value = {
            "token": "initial-token",
            "expirationTime": expiration_str,
        }
        mock_response1.raise_for_status = Mock()

        # Refresh response
        new_future = datetime.now(UTC) + timedelta(hours=1)
        new_expiration_str = new_future.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        mock_response2 = Mock()
        mock_response2.json.return_value = {
            "token": "refreshed-token",
            "expirationTime": new_expiration_str,
        }
        mock_response2.raise_for_status = Mock()

        mock_post.side_effect = [mock_response1, mock_response2]

        client = APIClient()

        # Access token property - should trigger refresh due to 30-minute buffer
        token = client.token

        assert token == "refreshed-token"
        assert mock_post.call_count == 2


@pytest.mark.local
class TestBrowserAuthentication:
    """Test browser-based OAuth authentication."""

    @patch.dict(os.environ, {"ENDOR_TOKEN": "", "ENDOR_AUTH_METHOD": ""}, clear=True)
    @patch("endor_cockpit.auth_server.get_token")
    @patch("endor_cockpit.api_client.requests.get")
    def test_browser_auth_method(self, mock_get, mock_get_token) -> None:
        """Test browser authentication method."""
        mock_get_token.return_value = "browser-token-123"

        mock_response = Mock()
        mock_response.json.return_value = {"version": "1.0.0"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = APIClient(auth_method="browser")

        assert client._auth_type == "browser"
        assert client._token == "browser-token-123"
        mock_get_token.assert_called_once()

    @patch.dict(os.environ, {"ENDOR_TOKEN": "", "ENDOR_AUTH_METHOD": ""}, clear=True)
    @patch("endor_cockpit.auth_server.get_token")
    @patch("endor_cockpit.api_client.requests.get")
    def test_browser_auth_with_provided_token(self, mock_get, mock_get_token) -> None:
        """Test browser auth with directly provided token."""
        mock_response = Mock()
        mock_response.json.return_value = {"version": "1.0.0"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = APIClient(token="direct-token-456", auth_method="browser")

        assert client._auth_type == "browser"
        assert client._token == "direct-token-456"
        # Should not call get_token if token is provided
        mock_get_token.assert_not_called()

    @patch.dict(
        os.environ,
        {
            "ENDOR_TOKEN": "env-token-789",
            "ENDOR_AUTH_METHOD": "browser",
        },
        clear=True,
    )
    @patch("endor_cockpit.api_client.requests.get")
    def test_browser_auth_from_env(self, mock_get) -> None:
        """Test browser auth from environment variables."""
        mock_response = Mock()
        mock_response.json.return_value = {"version": "1.0.0"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = APIClient()

        assert client._auth_type == "browser"
        assert client._token == "env-token-789"


class TestAuthenticationBackwardCompatibility:
    """Test backward compatibility with existing API key authentication."""

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
            "ENDOR_AUTH_METHOD": "",
        },
        clear=True,
    )
    @patch("endor_cockpit.api_client.requests.post")
    def test_api_key_auth_default(self, mock_post) -> None:
        """Test that API key auth is still the default."""
        mock_response = Mock()
        mock_response.json.return_value = {"token": "api-key-token"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = APIClient()

        assert client._auth_type == "api-key"
        assert client._token == "api-key-token"
        mock_post.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
            "ENDOR_AUTH_METHOD": "",
        },
        clear=True,
    )
    @patch("endor_cockpit.api_client.requests.post")
    def test_explicit_api_key_auth(self, mock_post) -> None:
        """Test explicit API key authentication method."""
        mock_response = Mock()
        mock_response.json.return_value = {"token": "api-key-token"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = APIClient(auth_method="api-key")

        assert client._auth_type == "api-key"
        assert client._token == "api-key-token"
