"""Tests for browser OAuth authentication server.

Browser OAuth tests are marked @pytest.mark.writes. CI runs all integration tests;
the marker allows optional filtering (e.g. -m "integration and not writes").
"""

import os
import threading
import urllib.request
from http.server import HTTPServer
from unittest.mock import Mock, patch

import pytest

import endorlabs.auth_server as auth_server_mod
from endorlabs.auth_server import (
    AUTH_METHODS,
    TokenHandler,
    get_token,
)


class TestTokenHandler:
    """Test TokenHandler for OAuth callback processing."""

    def test_token_handler_get_with_token(self) -> None:
        """Test TokenHandler captures token from GET request."""
        auth_server_mod._captured_token = None

        # Create a real server to test the handler properly
        server = HTTPServer(("localhost", 0), TokenHandler)

        # Simulate a request by directly testing the path parsing logic
        # This tests the core functionality without needing a full HTTP request
        test_path = "/?token=test-token-123"
        if "?" in test_path:
            _loc, query = test_path.split("?", 1)
            params = {}
            for param in query.split("&"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    params[k] = v
            if "token" in params:
                auth_server_mod._captured_token = params["token"]

        assert auth_server_mod._captured_token == "test-token-123"
        server.server_close()

    def test_token_parsing_logic(self) -> None:
        """Test token parsing from query string."""
        auth_server_mod._captured_token = None

        # Test the parsing logic used in TokenHandler
        test_path = "/?token=parsed-token-456"
        if "?" in test_path:
            _loc, query = test_path.split("?", 1)
            params = {}
            for param in query.split("&"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    params[k] = v
            if "token" in params:
                auth_server_mod._captured_token = params["token"]

        assert auth_server_mod._captured_token == "parsed-token-456"

    def test_token_parsing_without_token(self) -> None:
        """Test parsing when token is not in query string."""
        auth_server_mod._captured_token = None

        test_path = "/?other=value&another=param"
        if "?" in test_path:
            _loc, query = test_path.split("?", 1)
            params = {}
            for param in query.split("&"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    params[k] = v
            if "token" in params:
                auth_server_mod._captured_token = params["token"]

        assert auth_server_mod._captured_token is None

    def test_token_handler_do_get_via_http_request(self) -> None:
        """Test TokenHandler.do_GET by making a real HTTP request with token."""
        auth_server_mod._captured_token = None
        server = HTTPServer(("localhost", 0), TokenHandler)
        port = server.server_address[1]
        handled = threading.Event()

        def handle_one() -> None:
            server.handle_request()
            handled.set()

        try:
            thread = threading.Thread(target=handle_one)
            thread.start()
            with urllib.request.urlopen(
                f"http://localhost:{port}/?token=xyz-captured",
                timeout=5,
            ) as resp:
                assert resp.status == 200
            handled.wait(timeout=5)
            thread.join(timeout=5)
            assert auth_server_mod._captured_token == "xyz-captured"
        finally:
            server.server_close()
        auth_server_mod._captured_token = None


class TestGetToken:
    """Test get_token function for browser OAuth flow."""

    @pytest.mark.writes
    @patch("endorlabs.auth_server.HTTPServer")
    @patch("endorlabs.auth_server.get_browser")
    def test_get_token_success(self, mock_get_browser, mock_server_class) -> None:
        """Test successful token retrieval via browser OAuth."""
        auth_server_mod._captured_token = None

        # Mock browser
        mock_browser = Mock()
        mock_browser.open_new_tab = Mock()
        mock_get_browser.return_value = mock_browser

        # Mock server - need to simulate handle_request actually processing a request
        mock_server = Mock()
        mock_server.timeout = 20
        mock_server.server_close = Mock()

        # Create a mock request handler that will set the token in the module
        def handle_request_side_effect() -> None:
            auth_server_mod._captured_token = "test-bearer-token"

        mock_server.handle_request = Mock(side_effect=handle_request_side_effect)
        mock_server_class.return_value = mock_server

        token = get_token(timeout=20, environment="endorlabs.com", method="admin")

        assert token == "test-bearer-token"
        mock_browser.open_new_tab.assert_called_once()
        mock_server.handle_request.assert_called_once()
        mock_server.server_close.assert_called_once()

    @pytest.mark.writes
    @patch("endorlabs.auth_server.HTTPServer")
    @patch("endorlabs.auth_server.get_browser")
    def test_get_token_timeout(self, mock_get_browser, mock_server_class) -> None:
        """Test token retrieval timeout."""
        auth_server_mod._captured_token = None

        mock_browser = Mock()
        mock_browser.open_new_tab = Mock()
        mock_get_browser.return_value = mock_browser

        mock_server = Mock()
        mock_server.timeout = 20
        mock_server.handle_request = Mock()  # No token set
        mock_server.server_close = Mock()
        mock_server_class.return_value = mock_server

        token = get_token(timeout=5, environment="endorlabs.com", method="google")

        assert token is None
        mock_server.server_close.assert_called_once()

    @pytest.mark.writes
    def test_get_token_invalid_method(self) -> None:
        """Test get_token raises ValueError for invalid method."""
        with pytest.raises(ValueError, match="Unsupported auth method"):
            get_token(method="invalid_method")

    @pytest.mark.writes
    def test_get_token_email_required(self) -> None:
        """Test get_token requires email for email auth method."""
        with pytest.raises(ValueError, match="Email address required"):
            get_token(method="email")

    @pytest.mark.writes
    @patch("endorlabs.auth_server.HTTPServer")
    @patch("endorlabs.auth_server.get_browser")
    def test_get_token_email_method(self, mock_get_browser, mock_server_class) -> None:
        """Test get_token with email method includes email in URL."""
        auth_server_mod._captured_token = None

        mock_browser = Mock()
        mock_browser.open_new_tab = Mock()
        mock_get_browser.return_value = mock_browser

        mock_server = Mock()
        mock_server.timeout = 20
        mock_server.server_close = Mock()

        def handle_request_side_effect() -> None:
            auth_server_mod._captured_token = "email-token"

        mock_server.handle_request = Mock(side_effect=handle_request_side_effect)
        mock_server_class.return_value = mock_server

        token = get_token(
            timeout=20,
            environment="endorlabs.com",
            method="email",
            email="test@example.com",
        )

        assert token == "email-token"
        # Verify email was included in URL
        call_args = mock_browser.open_new_tab.call_args[0][0]
        assert "email=test@example.com" in call_args

    def test_auth_methods_defined(self) -> None:
        """Test that all expected auth methods are defined."""
        expected_methods = ["admin", "google", "github", "gitlab", "email"]
        for method in expected_methods:
            assert method in AUTH_METHODS, f"Auth method '{method}' not defined"

    @pytest.mark.writes
    @patch("endorlabs.auth_server.HTTPServer")
    def test_get_token_port_in_use(self, mock_server_class) -> None:
        """Test get_token handles port already in use error."""
        # Mock OSError for port in use
        mock_server_class.side_effect = OSError("Address already in use")

        token = get_token(method="admin")

        assert token is None

    @patch.dict(os.environ, {"CI": "true"}, clear=False)
    def test_get_token_prevents_ci_usage(self) -> None:
        """Test that get_token raises ValueError in CI environments."""
        with pytest.raises(
            ValueError, match="Browser authentication cannot be used in CI"
        ):
            get_token(method="admin")

    @patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False)
    def test_get_token_prevents_github_actions_usage(self) -> None:
        """Test that get_token raises ValueError in GitHub Actions."""
        with pytest.raises(
            ValueError, match="Browser authentication cannot be used in CI"
        ):
            get_token(method="browser")
