"""Tests for APIClient authentication with token expiration tracking.

Browser auth tests are marked @pytest.mark.writes. CI runs all integration tests;
the marker allows optional filtering (e.g. -m "integration and not writes").
"""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import httpx
import pytest

from endorlabs.api_client import APIClient
from endorlabs.core.exceptions import ValidationError


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


def _v1_auth_get_response(
    expiration_time: str | None = None,
    *,
    status_code: int = 200,
) -> Mock:
    """Build mock httpx-like response for GET /v1/auth token verification."""
    future_time = datetime.now(UTC) + timedelta(hours=4)
    expiration = expiration_time or future_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    mock = Mock()
    mock.json.return_value = {
        "authentication_source": "test-source",
        "expiration_time": expiration,
        "user": {"spec": {"email": "user@example.com"}},
    }
    mock.status_code = status_code
    mock.text = ""
    mock.url = "https://api.endorlabs.com/v1/auth"
    mock.headers = {}
    if status_code >= 400:
        mock.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"{status_code}",
            request=Mock(),
            response=mock,
        )
    else:
        mock.raise_for_status = Mock()
    return mock


def _auth_get_response() -> Mock:
    """Backward-compatible alias for browser token validation mocks."""
    return _v1_auth_get_response()


def _patch_httpx_client(
    post_return: Mock | list[Mock] | None = None,
    get_return: Mock | list[Mock] | None = None,
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
    if isinstance(get_return, list):
        mock_http.get.side_effect = get_return
    else:
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

    @patch.dict(
        os.environ,
        {"ENDOR_TOKEN": "direct-bearer-token", "ENDOR_API_CREDENTIALS_KEY": ""},
        clear=True,
    )
    def test_bearer_validation_uses_v1_auth_and_stores_expiration(self) -> None:
        """Provided bearer tokens validate via GET /v1/auth, not meta/version."""
        future_time = datetime.now(UTC) + timedelta(hours=4)
        expiration_str = future_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        verify_response = _v1_auth_get_response(expiration_str)
        verify_response.json.return_value["authentication_source"] = "google"

        with _patch_httpx_client(get_return=verify_response):
            client = APIClient(token="direct-bearer-token")

        assert client._auth_type == "browser"
        assert client._token == "direct-bearer-token"
        assert client._token_expires is not None
        assert client._token_expiration_source == "v1_auth"
        assert client.client.get.call_count >= 1
        get_urls = [str(c.args[0]) for c in client.client.get.call_args_list]
        assert any("v1/auth" in url for url in get_urls)
        assert not any("meta/version" in url for url in get_urls)

    @patch.dict(os.environ, {"ENDOR_TOKEN": ""}, clear=True)
    def test_bearer_expired_raises_refresh_hint(self) -> None:
        """Expired bearer sessions should fail closed on token access."""
        from endorlabs.core.exceptions import UnauthorizedError

        expired = datetime.now(UTC) - timedelta(minutes=5)
        near_expired = _v1_auth_get_response(expired.strftime("%Y-%m-%dT%H:%M:%SZ"))

        with _patch_httpx_client(get_return=near_expired):
            client = APIClient(auth_method="browser-auth")
            client._apply_session_token(
                "stale-token",
                expiration=expired,
                expiration_source="v1_auth",
                browser_validated=True,
            )
            with pytest.raises(UnauthorizedError, match="endor-auth refresh"):
                _ = client.token


@pytest.mark.writes
class TestBrowserAuthentication:
    """Test browser-based OAuth authentication."""

    @patch.dict(os.environ, {"ENDOR_TOKEN": ""}, clear=True)
    @patch("endorlabs.auth_server.get_token")
    def test_browser_auth_alias_normalizes_to_browser_auth(
        self, mock_get_token: Mock
    ) -> None:
        """`browser` alias should normalize to sso with insider tenant."""
        mock_get_token.return_value = "browser-token-123"

        with _patch_httpx_client(get_return=_auth_get_response()):
            client = APIClient(auth_method="browser")

        assert client.auth_method == "sso"
        assert client._auth_tenant == "endor-admin"
        assert client._auth_type == "browser"
        assert client._token == "browser-token-123"
        mock_get_token.assert_called_once()
        assert mock_get_token.call_args.kwargs["method"] == "sso"
        assert mock_get_token.call_args.kwargs["auth_tenant"] == "endor-admin"

    @patch.dict(os.environ, {"ENDOR_TOKEN": ""}, clear=True)
    @patch("endorlabs.auth_server.get_token")
    def test_browser_auth_method(self, mock_get_token: Mock) -> None:
        """Test browser authentication method."""
        mock_get_token.return_value = "browser-token-123"

        with _patch_httpx_client(get_return=_auth_get_response()):
            client = APIClient(auth_method="browser-auth")

        assert client._auth_type == "browser"
        assert client._token == "browser-token-123"
        mock_get_token.assert_called_once()

    @patch.dict(os.environ, {"ENDOR_TOKEN": ""}, clear=True)
    @patch("endorlabs.auth_server.get_token")
    def test_sso_auth_passes_tenant_to_browser_token_flow(
        self, mock_get_token: Mock
    ) -> None:
        """SSO auth should route with tenant to browser token flow."""
        mock_get_token.return_value = "browser-token-123"

        with _patch_httpx_client(get_return=_auth_get_response()):
            client = APIClient(auth_method="sso", auth_tenant="auri")

        assert client.auth_method == "sso"
        assert client._auth_type == "browser"
        assert client._token == "browser-token-123"
        mock_get_token.assert_called_once()
        assert mock_get_token.call_args.kwargs["method"] == "sso"
        assert mock_get_token.call_args.kwargs["auth_tenant"] == "auri"

    @patch.dict(os.environ, {"ENDOR_TOKEN": ""}, clear=True)
    @patch("endorlabs.auth_server.get_token")
    def test_browser_auth_with_provided_token(self, mock_get_token: Mock) -> None:
        """Test browser auth with directly provided token."""
        with _patch_httpx_client(get_return=_auth_get_response()):
            client = APIClient(token="direct-token-456", auth_method="browser")

        assert client._auth_type == "browser"
        assert client._token == "direct-token-456"
        # Should not call get_token if token is provided
        mock_get_token.assert_not_called()

    @patch.dict(os.environ, {"ENDOR_TOKEN": ""}, clear=True)
    @patch("endorlabs.auth_server.get_token")
    def test_browser_auth_with_invalid_provided_token_fails_closed(
        self, mock_get_token: Mock
    ) -> None:
        """Invalid provided token should not trigger browser fallback."""
        invalid_response = _v1_auth_get_response(status_code=401)

        with _patch_httpx_client(get_return=invalid_response):
            client = APIClient(token="invalid-token", auth_method="browser")

        assert client._auth_type == "browser"
        assert client._token is None
        mock_get_token.assert_not_called()

    @patch.dict(os.environ, {"ENDOR_TOKEN": ""}, clear=True)
    @patch("endorlabs.auth_server.get_token")
    def test_browser_auth_with_invalid_provided_token_keeps_browser_closed(
        self, mock_get_token: Mock
    ) -> None:
        """Invalid provided token should return no token and not open browser."""
        invalid_response = _v1_auth_get_response(status_code=401)

        with _patch_httpx_client(get_return=invalid_response):
            client = APIClient(token="invalid-token", auth_method="browser")

        assert client._auth_type == "browser"
        assert client._token is None
        mock_get_token.assert_not_called()

    @patch.dict(
        os.environ,
        {
            "ENDOR_TOKEN": "env-token-789",
            "ENDOR_NAMESPACE": "customer.child",
        },
        clear=True,
    )
    def test_token_from_env_learns_method_from_authentication_source(self) -> None:
        """Bearer method should persist from GET /v1/auth when env method unset."""
        auth_response = _v1_auth_get_response()
        auth_response.json.return_value["authentication_source"] = "google"

        with _patch_httpx_client(get_return=auth_response):
            client = APIClient()

        assert client.auth_method == "google"
        assert client._auth_method_pending_resolution is False

    @patch.dict(os.environ, {"ENDOR_TOKEN": "env-token-789"}, clear=True)
    @patch(
        "endorlabs.workflows.auth.env_resolution.resolve_sso_tenant",
        return_value=None,
    )
    def test_token_from_env_without_learnable_method_raises(
        self, mock_resolve: Mock
    ) -> None:
        """Bearer without /v1/auth provider hints or namespace should fail."""
        assert mock_resolve.return_value is None
        auth_response = _v1_auth_get_response()
        auth_response.json.return_value["authentication_source"] = "unknown-provider"

        with (
            pytest.raises(
                ValidationError, match="Cannot determine bearer refresh hint"
            ),
            _patch_httpx_client(get_return=auth_response),
        ):
            _ = APIClient()

    @patch.dict(
        os.environ,
        {
            "ENDOR_TOKEN": "env-token-789",
            "ENDOR_NAMESPACE": "customer.child",
        },
        clear=True,
    )
    def test_expired_bearer_raises_refresh_hint_with_learned_google_method(
        self,
    ) -> None:
        """Expired bearer tokens fail closed with a method-specific refresh hint."""
        from endorlabs.core.exceptions import UnauthorizedError

        past = datetime.now(UTC) - timedelta(hours=1)

        initial_valid = _v1_auth_get_response()
        initial_valid.json.return_value["user"] = {
            "spec": {"email": "user@corp@google"}
        }

        with _patch_httpx_client(get_return=initial_valid):
            client = APIClient()
            client._token_expires = past
            with pytest.raises(
                UnauthorizedError,
                match=r"endor-auth refresh --method google",
            ):
                _ = client.token

        assert client.auth_method == "google"

    @patch.dict(
        os.environ,
        {
            "ENDOR_TOKEN": "env-token-789",
            "ENDOR_NAMESPACE": "customer.child",
        },
        clear=True,
    )
    def test_bearer_expiry_warning_prints_to_stderr_once(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Proactive bearer expiry should warn on stderr without printing the token."""
        future = datetime.now(UTC) + timedelta(minutes=20)
        expiration_str = future.strftime("%Y-%m-%dT%H:%M:%SZ")
        auth_response = _v1_auth_get_response(expiration_str)
        auth_response.json.return_value["user"] = {
            "spec": {"email": "user@corp@google"}
        }

        with _patch_httpx_client(get_return=auth_response):
            client = APIClient()
            _ = client.token
            _ = client.token

        err = capsys.readouterr().err
        assert err.count("warning: Bearer token expires in") == 1
        assert "endor-auth refresh" in err
        assert "env-token-789" not in err

    @patch.dict(os.environ, {"ENDOR_TOKEN": ""}, clear=True)
    @patch("endorlabs.auth_server.get_token")
    def test_browser_token_reads_do_not_reopen_browser_session(
        self, mock_get_token: Mock
    ) -> None:
        """Once browser token is validated, repeated reads should not reauth."""
        mock_get_token.return_value = "browser-token-123"
        with _patch_httpx_client(get_return=_auth_get_response()):
            client = APIClient(auth_method="browser")
            # Session-like UX: repeated token reads should not trigger browser auth.
            first = client.token
            second = client.token

        assert first == "browser-token-123"
        assert second == "browser-token-123"
        mock_get_token.assert_called_once()

    @patch.dict(os.environ, {"ENDOR_TOKEN": ""}, clear=True)
    def test_browser_401_raises_refresh_hint_without_browser_reauth(self) -> None:
        """Bearer/browser sessions fail closed on 401 instead of reopening browser auth."""
        from endorlabs.core.exceptions import UnauthorizedError

        initial_valid = _v1_auth_get_response()

        with _patch_httpx_client(get_return=initial_valid):
            client = APIClient(token="direct-token", auth_method="browser")

            unauthorized = Mock()
            unauthorized.status_code = 401
            unauthorized.url = "https://api.endorlabs.com/v1/projects"
            unauthorized.headers = {}
            unauthorized.text = "Unauthorized"
            unauthorized.raise_for_status.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=Mock(),
                response=unauthorized,
            )

            with pytest.raises(UnauthorizedError, match="endor-auth refresh"):
                client._handle_response(unauthorized, method="GET", url="/v1/projects")


class TestAuthenticationBackwardCompatibility:
    """Test backward compatibility with existing API key authentication."""

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_api_key_auth_default(self) -> None:
        """Test that API key auth is still the default."""
        with _patch_httpx_client(post_return=_auth_post_response("api-key-token")):
            client = APIClient()

        assert client._auth_type == "api-key"
        assert client._token == "api-key-token"

    @patch.dict(
        os.environ,
        {
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_invalid_auth_method_fails_fast(self) -> None:
        """Unknown auth modes should raise clear startup validation errors."""
        with (
            pytest.raises(ValidationError, match="Unsupported auth_method"),
            _patch_httpx_client(get_return=_auth_get_response()),
        ):
            _ = APIClient(auth_method="bad-mode")

    @patch.dict(
        os.environ,
        {
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_email_mode_requires_email(self) -> None:
        """Email auth mode should require email input."""
        with (
            pytest.raises(ValidationError, match="requires email"),
            _patch_httpx_client(get_return=_auth_get_response()),
        ):
            _ = APIClient(auth_method="email")

    @patch.dict(
        os.environ,
        {
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_sso_mode_requires_auth_tenant(self) -> None:
        """SSO mode should require explicit or resolvable auth_tenant."""
        with (
            patch(
                "endorlabs.workflows.auth.env_resolution.resolve_sso_tenant",
                return_value=None,
            ),
            pytest.raises(ValidationError, match="requires auth_tenant"),
            _patch_httpx_client(get_return=_auth_get_response()),
        ):
            _ = APIClient(auth_method="sso")

    @patch.dict(
        os.environ,
        {
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_azureadv2_mode_fails_fast_until_supported(self) -> None:
        """azureadv2 is recognized but intentionally not yet implemented."""
        with (
            pytest.raises(ValidationError, match="not implemented"),
            _patch_httpx_client(get_return=_auth_get_response()),
        ):
            _ = APIClient(auth_method="azureadv2")

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_explicit_api_key_auth(self) -> None:
        """Test explicit API key authentication method."""
        with _patch_httpx_client(post_return=_auth_post_response("api-key-token")):
            client = APIClient(auth_method="api-key")

        assert client._auth_type == "api-key"
        assert client._token == "api-key-token"

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_api_key_auth_missing_token_field_fails_fast(self) -> None:
        """Malformed auth responses should fail with explicit startup error."""
        malformed = Mock()
        malformed.raise_for_status = Mock()
        malformed.json.return_value = {"unexpected": "value"}

        with (
            _patch_httpx_client(post_return=malformed),
            pytest.raises(
                ValidationError, match="Invalid auth response: missing token"
            ),
        ):
            _ = APIClient(auth_method="api-key")


class TestReauthRetryGuard:
    """Verify _handle_response does not infinite-loop on repeated 401s."""

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
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


class TestDualAuthEnv:
    @patch.dict(
        os.environ,
        {
            "ENDOR_TOKEN": "env-token",
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_NAMESPACE": "tenant.ns",
        },
        clear=True,
    )
    def test_dual_auth_logs_info_and_prefers_token(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        auth_response = _auth_get_response()
        auth_response.json.return_value["user"] = {
            "spec": {"email": "user@corp@google"}
        }
        with caplog.at_level("INFO", logger="endorlabs.api_client"):
            with _patch_httpx_client(get_return=auth_response):
                client = APIClient()
        assert client.auth_method == "google"
        assert client._auth_type == "browser"
        messages = " ".join(record.message for record in caplog.records)
        assert "ENDOR_TOKEN" in messages
        assert "ENDOR_API_CREDENTIALS_KEY" in messages
        assert "errors-and-auth" in messages

    @patch.dict(
        os.environ, {"ENDOR_TOKEN": "", "ENDOR_API_CREDENTIALS_KEY": ""}, clear=True
    )
    def test_missing_credentials_mentions_endor_token(self) -> None:
        with pytest.raises(ValidationError, match="ENDOR_TOKEN"):
            APIClient()
