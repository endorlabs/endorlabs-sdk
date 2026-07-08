"""Tests for APIClient configuration via environment variables.

Tests ENDOR_MAX_RETRIES and ENDOR_LOG_LEVEL environment variables,
and verifies backward compatibility is removed for LOG_LEVEL.
"""

import logging
import os
from unittest.mock import Mock, patch

import pytest

from endorlabs.api_client import DEFAULT_API_BASE_URL, APIClient
from endorlabs.core.exceptions import ValidationError
from endorlabs.utils.logging_config import setup_logging


def _make_auth_response_mock(token: str = "test-token") -> Mock:
    """Return a mock httpx-like response for auth endpoint."""
    mock_response = Mock()
    mock_response.json.return_value = {"token": token}
    mock_response.raise_for_status = Mock()
    mock_response.status_code = 200
    mock_response.text = ""
    mock_response.url = "https://api.endorlabs.com/v1/auth/api-key"
    mock_response.headers = {}
    return mock_response


def _patch_httpx_client_for_auth(post_return: Mock | None = None) -> Mock:
    """Patch httpx.Client so APIClient gets a mock; post_return is returned by post."""
    if post_return is None:
        post_return = _make_auth_response_mock()
    mock_http = Mock()
    mock_http.post.return_value = post_return
    mock_http.get.return_value = _make_auth_response_mock()
    return patch("endorlabs.api_client.httpx.Client", return_value=mock_http)


class TestEndorMaxRetries:
    """Test ENDOR_MAX_RETRIES environment variable."""

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_MAX_RETRIES": "3",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_endor_max_retries_from_env(self) -> None:
        """Test that ENDOR_MAX_RETRIES environment variable is respected."""
        with _patch_httpx_client_for_auth():
            client = APIClient()

        assert client.max_retries == 3

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_MAX_RETRIES": "7",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_endor_max_retries_custom_value(self) -> None:
        """Test ENDOR_MAX_RETRIES with custom value."""
        with _patch_httpx_client_for_auth():
            client = APIClient()

        assert client.max_retries == 7

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_max_retries_default_when_env_not_set(self) -> None:
        """Test default max_retries=5 when ENDOR_MAX_RETRIES not set."""
        with _patch_httpx_client_for_auth():
            client = APIClient()

        assert client.max_retries == 5

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_MAX_RETRIES": "3",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_parameter_override_takes_precedence(self) -> None:
        """Test that parameter override takes precedence over env var."""
        with _patch_httpx_client_for_auth():
            # ENDOR_MAX_RETRIES is set to 3, but we pass 10 explicitly
            client = APIClient(max_retries=10)

        assert client.max_retries == 10


class TestDefaultApiBaseUrl:
    """Test ENDOR_API default without mutating process environment."""

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_constructor_does_not_set_endor_api_env(self) -> None:
        with _patch_httpx_client_for_auth():
            client = APIClient()
        assert os.getenv("ENDOR_API") is None
        assert client.base_url == DEFAULT_API_BASE_URL


class TestRequestTimeout:
    """Test timeout and Request-timeout header (ENDOR_REQUEST_TIMEOUT)."""

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_timeout_param_sets_header(self) -> None:
        """APIClient(timeout=30) sets client.timeout and Request-timeout: 30."""
        with _patch_httpx_client_for_auth():
            client = APIClient(timeout=30.0)
        assert client.timeout == 30.0
        assert client._request_headers.get("Request-timeout") == "30"

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_REQUEST_TIMEOUT": "20",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_endor_request_timeout_from_env(self) -> None:
        """ENDOR_REQUEST_TIMEOUT is used when default timeout is used."""
        with _patch_httpx_client_for_auth():
            client = APIClient()
        assert client.timeout == 20.0
        assert client._request_headers.get("Request-timeout") == "20"

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_REQUEST_TIMEOUT": "15",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_timeout_parameter_override_takes_precedence(self) -> None:
        """timeout=45 overrides ENDOR_REQUEST_TIMEOUT."""
        with _patch_httpx_client_for_auth():
            client = APIClient(timeout=45.0)
        assert client.timeout == 45.0
        assert client._request_headers.get("Request-timeout") == "45"

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_API_TIMEOUT": "25",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_endor_api_timeout_from_env(self) -> None:
        """ENDOR_API_TIMEOUT is used when request timeout env is unset."""
        with _patch_httpx_client_for_auth():
            client = APIClient()
        assert client.timeout == 25.0
        assert client._request_headers.get("Request-timeout") == "25"

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_REQUEST_TIMEOUT": "90",
            "ENDOR_API_TIMEOUT": "25",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_endor_request_timeout_precedes_api_timeout(self) -> None:
        """ENDOR_REQUEST_TIMEOUT takes precedence over ENDOR_API_TIMEOUT."""
        with _patch_httpx_client_for_auth():
            client = APIClient()
        assert client.timeout == 90.0


class TestContentTypeAndAcceptEncoding:
    """Test content_type and accept_encoding (API header options)."""

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_content_type_application_json_sets_header(self) -> None:
        """content_type='application/json' sets Content-Type header."""
        with _patch_httpx_client_for_auth():
            client = APIClient(content_type="application/json")
        assert client.content_type == "application/json"
        assert client._request_headers.get("Content-Type") == "application/json"

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_accept_encoding_none_omits_header(self) -> None:
        """accept_encoding=None omits Accept-Encoding header."""
        with _patch_httpx_client_for_auth():
            client = APIClient(accept_encoding=None)
        assert client.accept_encoding is None
        assert "Accept-Encoding" not in client._request_headers

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_accept_encoding_empty_omits_header(self) -> None:
        """accept_encoding='' omits Accept-Encoding header."""
        with _patch_httpx_client_for_auth():
            client = APIClient(accept_encoding="")
        assert client.accept_encoding == ""
        assert "Accept-Encoding" not in client._request_headers


class TestEndorLogLevel:
    """Test ENDOR_LOG_LEVEL environment variable."""

    def test_endor_log_level_from_env(self) -> None:
        """Test that ENDOR_LOG_LEVEL environment variable is respected."""
        import logging

        with patch.dict(os.environ, {"ENDOR_LOG_LEVEL": "DEBUG"}, clear=False):
            logger = setup_logging("test_log_level_debug")
            assert logger.level == logging.DEBUG

    def test_endor_log_level_default_when_not_set(self) -> None:
        """Test default INFO level when ENDOR_LOG_LEVEL not set."""
        import logging

        # Remove ENDOR_LOG_LEVEL if it exists
        env_backup = os.environ.pop("ENDOR_LOG_LEVEL", None)
        try:
            logger = setup_logging("test_log_level_default")
            assert logger.level == logging.INFO
        finally:
            if env_backup:
                os.environ["ENDOR_LOG_LEVEL"] = env_backup

    def test_endor_log_level_warning(self) -> None:
        """Test ENDOR_LOG_LEVEL with WARNING value."""
        import logging

        with patch.dict(os.environ, {"ENDOR_LOG_LEVEL": "WARNING"}, clear=False):
            logger = setup_logging("test_log_level_warning")
            assert logger.level == logging.WARNING

    def test_endor_log_level_error(self) -> None:
        """Test ENDOR_LOG_LEVEL with ERROR value."""
        import logging

        with patch.dict(os.environ, {"ENDOR_LOG_LEVEL": "ERROR"}, clear=False):
            logger = setup_logging("test_log_level_error")
            assert logger.level == logging.ERROR

    def test_setup_logging_adds_null_handler(self) -> None:
        """Test that setup_logging adds a NullHandler (PEP 282 pattern)."""
        import logging

        logger = setup_logging("test_null_handler_check")
        assert any(isinstance(h, logging.NullHandler) for h in logger.handlers)


class TestClientSessionLogLevel:
    """Test that APIClient(logging_level=...) applies to all session loggers."""

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
        },
        clear=True,
    )
    def test_logging_level_applied_to_session_loggers(self) -> None:
        """APIClient(logging_level='ERROR') sets session loggers to ERROR."""
        # Save current levels so we don't affect other tests
        names = ("endorlabs", "httpx", "httpcore")
        saved = {n: logging.getLogger(n).level for n in names}
        try:
            with _patch_httpx_client_for_auth():
                client = APIClient(logging_level="ERROR")
            assert client.logger.level == logging.ERROR
            for name in names:
                assert logging.getLogger(name).level == logging.ERROR
        finally:
            for n, level in saved.items():
                logging.getLogger(n).setLevel(level)


class TestLogLevelBackwardCompatibility:
    """Test that LOG_LEVEL (old name) no longer works."""

    def test_log_level_no_longer_works(self) -> None:
        """Test that LOG_LEVEL environment variable is ignored."""
        import logging

        # Set LOG_LEVEL but not ENDOR_LOG_LEVEL
        with patch.dict(
            os.environ,
            {"LOG_LEVEL": "DEBUG", "ENDOR_LOG_LEVEL": ""},
            clear=False,
        ):
            # Remove ENDOR_LOG_LEVEL if it exists
            env_backup = os.environ.pop("ENDOR_LOG_LEVEL", None)
            try:
                logger = setup_logging("test_log_level_compat")
                # Should default to INFO, not DEBUG
                assert logger.level == logging.INFO
            finally:
                if env_backup:
                    os.environ["ENDOR_LOG_LEVEL"] = env_backup

    def test_endor_log_level_takes_precedence_over_log_level(self) -> None:
        """Test that ENDOR_LOG_LEVEL takes precedence if both are set."""
        import logging

        with patch.dict(
            os.environ,
            {"LOG_LEVEL": "DEBUG", "ENDOR_LOG_LEVEL": "WARNING"},
            clear=False,
        ):
            logger = setup_logging("test_log_level_precedence")
            # Should use ENDOR_LOG_LEVEL (WARNING), not LOG_LEVEL (DEBUG)
            assert logger.level == logging.WARNING


class TestRequestDelegation:
    """Each public HTTP method delegates to _request() with the correct method string.

    _request() consolidates rate-limiting, auth, URL normalization, header
    merging, logging, and retry into one place.  These tests verify the
    delegation contract by patching _request_with_retry (the lowest internal
    call site) and asserting the method string, normalized URL, and merged
    headers arrive correctly.
    """

    @staticmethod
    def _make_client() -> APIClient:
        """Build an APIClient with mocked transport for delegation tests."""
        with (
            patch.dict(
                os.environ,
                {
                    "ENDOR_API_CREDENTIALS_KEY": "test-key",
                    "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
                    "ENDOR_TOKEN": "",
                },
                clear=True,
            ),
            _patch_httpx_client_for_auth(),
        ):
            return APIClient()

    @pytest.mark.parametrize(
        "method_name",
        ["get", "post", "patch", "put", "delete"],
    )
    def test_method_delegates_with_correct_method_string(
        self, method_name: str
    ) -> None:
        """get/post/patch/put/delete pass the correct HTTP method string."""
        client = self._make_client()
        sentinel = Mock()
        mock_retry = Mock(return_value=sentinel)
        with patch.object(client, "_request_with_retry", mock_retry):
            fn = getattr(client, method_name)
            result = fn("/v1/namespaces")

        assert result is sentinel
        # First positional arg is the HTTP method
        assert mock_retry.call_args[0][0] == method_name.upper()

    def test_get_normalizes_relative_url(self) -> None:
        """Relative URL is prepended with base_url."""
        client = self._make_client()
        mock_retry = Mock(return_value=Mock())
        with patch.object(client, "_request_with_retry", mock_retry):
            client.get("/v1/namespaces")

        url = mock_retry.call_args[0][1]
        assert url.startswith("https://")
        assert url.endswith("/v1/namespaces")

    def test_post_passes_json_payload(self) -> None:
        """POST forwards the json kwarg to _request_with_retry."""
        client = self._make_client()
        payload = {"meta": {"name": "test"}}
        mock_retry = Mock(return_value=Mock())
        with patch.object(client, "_request_with_retry", mock_retry):
            client.post("/v1/namespaces", json=payload)

        assert mock_retry.call_args.kwargs.get("json") is payload

    def test_custom_headers_are_merged(self) -> None:
        """Extra headers passed to a method are merged with session headers."""
        client = self._make_client()
        custom = {"X-Custom": "value"}
        mock_retry = Mock(return_value=Mock())
        with patch.object(client, "_request_with_retry", mock_retry):
            client.get("/v1/namespaces", headers=custom)

        sent_headers = mock_retry.call_args.kwargs.get("headers", {})
        assert sent_headers.get("X-Custom") == "value"
        # Session headers (e.g. Content-Type) are also present
        assert "Content-Type" in sent_headers

    def test_params_forwarded(self) -> None:
        """Query params are forwarded to _request_with_retry."""
        client = self._make_client()
        mock_retry = Mock(return_value=Mock())
        with patch.object(client, "_request_with_retry", mock_retry):
            client.get("/v1/namespaces", params={"traverse": "true"})

        assert mock_retry.call_args.kwargs.get("params") == {"traverse": "true"}

    def test_absolute_url_same_host_is_allowed(self) -> None:
        """Absolute URLs to configured API host are allowed."""
        client = self._make_client()
        mock_retry = Mock(return_value=Mock())
        with patch.object(client, "_request_with_retry", mock_retry):
            client.get("https://api.endorlabs.com/v1/namespaces")

        url = mock_retry.call_args[0][1]
        assert url == "https://api.endorlabs.com/v1/namespaces"

    def test_absolute_url_different_host_is_rejected(self) -> None:
        """Absolute URLs to untrusted hosts are rejected before request."""
        client = self._make_client()

        with pytest.raises(ValidationError, match="disallowed host"):
            client.get("https://evil.example.test/v1/namespaces")

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_TOKEN": "",
            "ENDOR_ALLOWED_API_HOSTS": "api.staging.endorlabs.com",
        },
        clear=True,
    )
    def test_absolute_url_allowlist_env_host_is_allowed(self) -> None:
        """Explicit allowlist hosts permit trusted multi-env absolute URLs."""
        with _patch_httpx_client_for_auth():
            client = APIClient()
        mock_retry = Mock(return_value=Mock())
        with patch.object(client, "_request_with_retry", mock_retry):
            client.get("https://api.staging.endorlabs.com/v1/namespaces")

        url = mock_retry.call_args[0][1]
        assert url == "https://api.staging.endorlabs.com/v1/namespaces"
