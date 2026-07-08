"""Tests for browser OAuth authentication server.

get_token() rejects CI environments before mocks apply (see
test_get_token_prevents_ci_usage). Other get_token() tests use
@pytest.mark.interactive and are excluded in CI (-m "not interactive").
Run locally: pytest tests/unit/platform/transport/test_auth_server.py -m interactive.
For a real browser token, use `uv run endor-auth refresh` — not pytest.
"""

import os
import threading
import urllib.parse
import urllib.request
from http.server import HTTPServer
from unittest.mock import Mock, patch

import pytest

import endorlabs.auth_server as auth_server_mod
from endorlabs.auth_server import (
    AUTH_METHODS,
    _append_query_params,
    _bind_callback_server,
    _make_token_handler,
    get_token,
)
from endorlabs.core.exceptions import ValidationError

_TEST_STATE = "expected-oauth-state"


def _run_handler_request(
    handler_cls: type,
    query: str,
) -> tuple[int | None, str | None]:
    """Start a one-shot server and return (HTTP status, captured token)."""
    auth_server_mod._captured_token = None
    server = HTTPServer(("localhost", 0), handler_cls)
    port = server.server_address[1]
    handled = threading.Event()

    def handle_one() -> None:
        server.handle_request()
        handled.set()

    status: int | None = None
    thread = threading.Thread(target=handle_one)
    try:
        thread.start()
        with urllib.request.urlopen(
            f"http://localhost:{port}/?{query}",
            timeout=5,
        ) as resp:
            status = resp.status
        handled.wait(timeout=5)
    except urllib.error.HTTPError as exc:
        status = exc.code
        handled.wait(timeout=5)
    finally:
        thread.join(timeout=5)
        server.server_close()
    return status, auth_server_mod._captured_token


class TestTokenHandler:
    """Test TokenHandler for OAuth callback processing."""

    def test_token_handler_do_get_via_http_request(self) -> None:
        """Test handler captures token when state matches."""
        handler = _make_token_handler(_TEST_STATE)
        status, token = _run_handler_request(
            handler,
            f"token=xyz-captured&state={_TEST_STATE}",
        )
        assert status == 200
        assert token == "xyz-captured"

    def test_token_handler_accepts_token_without_state(self) -> None:
        """CLI redirect currently returns token only; capture must still work."""
        handler = _make_token_handler(_TEST_STATE)
        status, token = _run_handler_request(
            handler,
            "token=cli-redirect-token",
        )
        assert status == 200
        assert token == "cli-redirect-token"

    def test_token_handler_decodes_urlencoded_token(self) -> None:
        """Token from query string should be URL-decoded."""
        handler = _make_token_handler(_TEST_STATE)
        status, token = _run_handler_request(
            handler,
            f"token=abc%2Bdef%3D%3D&state={_TEST_STATE}",
        )
        assert status == 200
        assert token == "abc+def=="

    def test_token_handler_rejects_state_mismatch(self) -> None:
        """Callback with wrong state must not capture token."""
        handler = _make_token_handler(_TEST_STATE)
        status, token = _run_handler_request(
            handler,
            "token=ignored&state=wrong-state",
        )
        assert status == 400
        assert token is None

    def test_token_handler_rejects_multiple_token_values(self) -> None:
        """Ambiguous token query should not capture a token."""
        handler = _make_token_handler(_TEST_STATE)
        _status, token = _run_handler_request(
            handler,
            f"token=first&token=second&state={_TEST_STATE}",
        )
        assert token is None


class TestAuthUrlHelpers:
    """URL helper tests."""

    def test_append_query_params_urlencodes_email(self) -> None:
        url = _append_query_params(
            "https://api.endorlabs.com/v1/auth/login",
            {"email": "user+alias@example.com", "redirect": "cli"},
        )
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        assert params["email"] == ["user+alias@example.com"]
        assert params["redirect"] == ["cli"]


class TestGetToken:
    """Test get_token function for browser OAuth flow."""

    def _mock_bind_server(self, mock_bind: Mock) -> Mock:
        mock_server = Mock()
        mock_server.timeout = 20
        mock_server.server_close = Mock()

        def handle_request_side_effect() -> None:
            auth_server_mod._captured_token = "test-bearer-token"

        mock_server.handle_request = Mock(side_effect=handle_request_side_effect)
        mock_bind.return_value = (mock_server, 30000)
        return mock_server

    @pytest.mark.interactive
    @pytest.mark.writes
    @patch("endorlabs.auth_server._bind_callback_server")
    @patch("endorlabs.auth_server.get_browser")
    def test_get_token_browser_alias_maps_to_browser_auth(
        self, mock_get_browser, mock_bind
    ) -> None:
        """Legacy browser alias should still work via browser-auth mapping."""
        auth_server_mod._captured_token = None
        mock_browser = Mock()
        mock_browser.open_new_tab = Mock()
        mock_get_browser.return_value = mock_browser
        mock_server = self._mock_bind_server(mock_bind)
        mock_server.handle_request.side_effect = lambda: setattr(
            auth_server_mod, "_captured_token", "alias-token"
        )

        token = get_token(timeout=20, environment="endorlabs.com", method="browser")
        assert token == "alias-token"
        mock_browser.open_new_tab.assert_called_once()
        auth_url = mock_browser.open_new_tab.call_args[0][0]
        assert "state=" in auth_url

    @pytest.mark.interactive
    @pytest.mark.writes
    @patch("endorlabs.auth_server._bind_callback_server")
    @patch("endorlabs.auth_server.get_browser")
    def test_get_token_success(self, mock_get_browser, mock_bind) -> None:
        """Test successful token retrieval via browser OAuth."""
        auth_server_mod._captured_token = None
        mock_browser = Mock()
        mock_browser.open_new_tab = Mock()
        mock_get_browser.return_value = mock_browser
        mock_server = self._mock_bind_server(mock_bind)

        token = get_token(timeout=20, environment="endorlabs.com", method="admin")

        assert token == "test-bearer-token"
        mock_browser.open_new_tab.assert_called_once()
        mock_server.handle_request.assert_called_once()
        mock_server.server_close.assert_called_once()

    @pytest.mark.interactive
    @pytest.mark.writes
    @patch("endorlabs.auth_server._bind_callback_server")
    @patch("endorlabs.auth_server.get_browser")
    def test_get_token_timeout(self, mock_get_browser, mock_bind) -> None:
        """Test token retrieval timeout."""
        auth_server_mod._captured_token = None
        mock_browser = Mock()
        mock_browser.open_new_tab = Mock()
        mock_get_browser.return_value = mock_browser
        mock_server = Mock()
        mock_server.timeout = 20
        mock_server.handle_request = Mock()
        mock_server.server_close = Mock()
        mock_bind.return_value = (mock_server, 30000)

        token = get_token(timeout=5, environment="endorlabs.com", method="google")

        assert token is None
        mock_server.server_close.assert_called_once()

    @pytest.mark.interactive
    @pytest.mark.writes
    def test_get_token_invalid_method(self) -> None:
        """Test get_token raises ValueError for invalid method."""
        with pytest.raises(ValidationError, match="Unsupported auth method"):
            get_token(method="invalid_method")

    @pytest.mark.interactive
    @pytest.mark.writes
    def test_get_token_email_required(self) -> None:
        """Test get_token requires email for email auth method."""
        with pytest.raises(ValidationError, match="Email address required"):
            get_token(method="email")

    @pytest.mark.interactive
    @pytest.mark.writes
    @patch("endorlabs.auth_server._bind_callback_server")
    @patch("endorlabs.auth_server.get_browser")
    def test_get_token_email_method(self, mock_get_browser, mock_bind) -> None:
        """Test get_token with email method includes encoded email in URL."""
        auth_server_mod._captured_token = None
        mock_browser = Mock()
        mock_browser.open_new_tab = Mock()
        mock_get_browser.return_value = mock_browser
        mock_server = self._mock_bind_server(mock_bind)
        mock_server.handle_request.side_effect = lambda: setattr(
            auth_server_mod, "_captured_token", "email-token"
        )

        token = get_token(
            timeout=20,
            environment="endorlabs.com",
            method="email",
            email="user+alias@example.com",
        )

        assert token == "email-token"
        call_args = mock_browser.open_new_tab.call_args[0][0]
        parsed = urllib.parse.urlparse(call_args)
        params = urllib.parse.parse_qs(parsed.query)
        assert params["email"] == ["user+alias@example.com"]

    def test_auth_methods_defined(self) -> None:
        """Test that all expected auth methods are defined."""
        expected_methods = [
            "browser-auth",
            "sso",
            "admin",
            "google",
            "github",
            "gitlab",
            "email",
        ]
        for method in expected_methods:
            assert method in AUTH_METHODS, f"Auth method '{method}' not defined"

    @pytest.mark.interactive
    @pytest.mark.writes
    @patch("endorlabs.auth_server._bind_callback_server")
    def test_get_token_port_in_use(self, mock_bind) -> None:
        """Test get_token handles port already in use error."""
        mock_bind.side_effect = OSError("Address already in use")

        token = get_token(method="admin")

        assert token is None

    def test_bind_callback_server_uses_port_range(self) -> None:
        """First free port in the CLI range should bind successfully."""
        server, port = _bind_callback_server("bind-test-state")
        try:
            assert 30000 <= port < 30000 + 10
        finally:
            server.server_close()

    @patch.dict(os.environ, {"CI": "true"}, clear=False)
    def test_get_token_prevents_ci_usage(self) -> None:
        """Test that get_token raises ValueError in CI environments."""
        with pytest.raises(
            ValidationError, match="Browser authentication cannot be used in CI"
        ):
            get_token(method="admin")

    @patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False)
    def test_get_token_prevents_github_actions_usage(self) -> None:
        """Test that get_token raises ValueError in GitHub Actions."""
        with pytest.raises(
            ValidationError, match="Browser authentication cannot be used in CI"
        ):
            get_token(method="browser-auth")

    @pytest.mark.interactive
    @pytest.mark.writes
    def test_get_token_sso_requires_tenant(self) -> None:
        """SSO mode should require auth_tenant."""
        with pytest.raises(ValidationError, match="Tenant is required for sso"):
            get_token(method="sso")
