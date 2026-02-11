"""Tests for APIClient authentication with token expiration tracking.

Browser auth tests are marked @pytest.mark.writes. CI runs all integration tests;
the marker allows optional filtering (e.g. -m "integration and not writes").
"""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from endorlabs.api_client import APIClient


def _auth_post_response(
    token: str = "test-token", expiration_time: str | None = None
) -> Mock:
    """Build mock httpx-like response for auth api-key endpoint."""
    data: dict = {"token": token}
    if expiration_time is not None:
        data["expirationTime"] = expiration_time
        data["expiration_time"] = expiration_time
    mock = Mock()
    mock.json.return_value = data
    mock.raise_for_status = Mock()
    mock.status_code = 200
    mock.text = ""
    mock.url = "https://api.endorlabs.com/v1/auth/api-key"
    mock.headers = {}
    return mock


def _auth_get_response() -> Mock:
    """Build mock httpx-like response for meta/version (browser token validation)."""
    mock = Mock()
    mock.json.return_value = {"version": "1.0.0"}
    mock.raise_for_status = Mock()
    mock.status_code = 200
    mock.text = ""
    mock.url = "https://api.endorlabs.com/meta/version"
    mock.headers = {}
    return mock


def _patch_httpx_client(
    post_return: Mock | list[Mock] | None = None, get_return: Mock | None = None
) -> Mock:
    """Patch httpx.Client; post_return can be single mock or list for side_effect."""
    if post_return is None:
        post_return = _auth_post_response()
    if get_return is None:
        get_return = _auth_get_response()
    mock_http = Mock()
    if isinstance(post_return, list):
        mock_http.post.side_effect = post_return
    else:
        mock_http.post.return_value = post_return
    mock_http.get.return_value = get_return
    return patch("endorlabs.api_client.httpx.Client", return_value=mock_http)


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
    def test_token_expiration_parsing(self) -> None:
        """Test that token expiration is parsed from API response."""
        # Mock response with expiration
        future_time = datetime.now(UTC) + timedelta(hours=1)
        expiration_str = future_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        mock_response = _auth_post_response("test-token", expiration_str)

        with _patch_httpx_client(post_return=mock_response):
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
    def test_token_expiration_alternative_field(self) -> None:
        """Test parsing expiration_time field (alternative to expirationTime)."""
        future_time = datetime.now(UTC) + timedelta(hours=1)
        expiration_str = future_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        mock_response = _auth_post_response("test-token", expiration_str)

        with _patch_httpx_client(post_return=mock_response):
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
    def test_token_property_refresh(self) -> None:
        """Test token property triggers refresh when expired."""
        # First authentication
        future_time = datetime.now(UTC) + timedelta(minutes=10)
        expiration_str = future_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        mock_response1 = _auth_post_response("initial-token", expiration_str)

        # Second authentication (refresh)
        new_future_time = datetime.now(UTC) + timedelta(hours=1)
        new_expiration_str = new_future_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        mock_response2 = _auth_post_response("refreshed-token", new_expiration_str)

        with _patch_httpx_client(post_return=[mock_response1, mock_response2]):
            client = APIClient()

            # Manually set expiration to past to trigger refresh
            client._token_expires = datetime.now(UTC) - timedelta(hours=1)

            # Access token property should trigger refresh
            token = client.token

            assert token == "refreshed-token"
            assert client.client.post.call_count == 2

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
    def test_is_expired_property(self) -> None:
        """Test is_expired property correctly identifies expired tokens."""
        future_time = datetime.now(UTC) + timedelta(hours=1)
        expiration_str = future_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        mock_response = _auth_post_response("test-token", expiration_str)

        with _patch_httpx_client(post_return=mock_response):
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
    def test_proactive_refresh_30_minutes(self) -> None:
        """Test proactive refresh triggers 30 minutes before expiration."""
        # Set expiration to 25 minutes from now (within 30-minute buffer)
        near_future = datetime.now(UTC) + timedelta(minutes=25)
        expiration_str = near_future.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        mock_response1 = _auth_post_response("initial-token", expiration_str)

        # Refresh response
        new_future = datetime.now(UTC) + timedelta(hours=1)
        new_expiration_str = new_future.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        mock_response2 = _auth_post_response("refreshed-token", new_expiration_str)

        with _patch_httpx_client(post_return=[mock_response1, mock_response2]):
            client = APIClient()

            # Access token property - should trigger refresh due to 30-minute buffer
            token = client.token

            assert token == "refreshed-token"
            assert client.client.post.call_count == 2


@pytest.mark.writes
class TestBrowserAuthentication:
    """Test browser-based OAuth authentication."""

    @patch.dict(os.environ, {"ENDOR_TOKEN": "", "ENDOR_AUTH_METHOD": ""}, clear=True)
    @patch("endorlabs.auth_server.get_token")
    def test_browser_auth_method(self, mock_get_token: Mock) -> None:
        """Test browser authentication method."""
        mock_get_token.return_value = "browser-token-123"

        with _patch_httpx_client(get_return=_auth_get_response()):
            client = APIClient(auth_method="browser")

        assert client._auth_type == "browser"
        assert client._token == "browser-token-123"
        mock_get_token.assert_called_once()

    @patch.dict(os.environ, {"ENDOR_TOKEN": "", "ENDOR_AUTH_METHOD": ""}, clear=True)
    @patch("endorlabs.auth_server.get_token")
    def test_browser_auth_with_provided_token(self, mock_get_token: Mock) -> None:
        """Test browser auth with directly provided token."""
        with _patch_httpx_client(get_return=_auth_get_response()):
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
    def test_browser_auth_from_env(self) -> None:
        """Test browser auth from environment variables."""
        with _patch_httpx_client(get_return=_auth_get_response()):
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
    def test_api_key_auth_default(self) -> None:
        """Test that API key auth is still the default."""
        with _patch_httpx_client(post_return=_auth_post_response("api-key-token")):
            client = APIClient()

        assert client._auth_type == "api-key"
        assert client._token == "api-key-token"
        client.client.post.assert_called_once()

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
    def test_explicit_api_key_auth(self) -> None:
        """Test explicit API key authentication method."""
        with _patch_httpx_client(post_return=_auth_post_response("api-key-token")):
            client = APIClient(auth_method="api-key")

        assert client._auth_type == "api-key"
        assert client._token == "api-key-token"


class TestReauthRetryGuard:
    """Verify _handle_response does not infinite-loop on repeated 401s."""

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
    def test_401_no_infinite_recursion(self) -> None:
        """A second 401 after reauth must raise, not retry again."""
        import httpx

        with _patch_httpx_client(post_return=_auth_post_response("init-token")):
            client = APIClient()

        # Build a mock 401 response
        def _make_401() -> Mock:
            resp = Mock(spec=httpx.Response)
            resp.status_code = 401
            resp.url = "https://api.endorlabs.com/v1/namespaces/test/projects"
            resp.headers = {}
            resp.text = "Unauthorized"
            resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=Mock(),
                response=resp,
            )
            return resp

        # authenticate() succeeds but the retry still gets a 401
        with (
            patch.object(client, "authenticate", return_value="new-token"),
            patch.object(client, "client", create=True) as mock_inner_client,
        ):
            mock_inner_client.request.return_value = _make_401()

            with pytest.raises(httpx.HTTPStatusError):
                client._handle_response(
                    _make_401(), method="GET", url="/v1/namespaces/test/projects"
                )

            # authenticate should be called exactly once (not repeatedly)
            client.authenticate.assert_called_once()
