"""Tests for APIClient configuration via environment variables.

Tests ENDOR_MAX_RETRIES and ENDOR_LOG_LEVEL environment variables,
and verifies backward compatibility is removed for LOG_LEVEL.
"""

import logging
import os
from unittest.mock import Mock, patch

from endorlabs.api_client import APIClient
from endorlabs.utils.logging_config import setup_logging


class TestEndorMaxRetries:
    """Test ENDOR_MAX_RETRIES environment variable."""

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_MAX_RETRIES": "3",
            "ENDOR_TOKEN": "",
            "ENDOR_AUTH_METHOD": "",
        },
        clear=True,
    )
    @patch("endorlabs.api_client.requests.post")
    def test_endor_max_retries_from_env(self, mock_post) -> None:
        """Test that ENDOR_MAX_RETRIES environment variable is respected."""
        mock_response = Mock()
        mock_response.json.return_value = {"token": "test-token"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = APIClient()

        assert client.max_retries == 3
        # Verify retry adapter is configured with correct value
        assert client.session.adapters["https://"].max_retries.total == 3

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_MAX_RETRIES": "7",
            "ENDOR_TOKEN": "",
            "ENDOR_AUTH_METHOD": "",
        },
        clear=True,
    )
    @patch("endorlabs.api_client.requests.post")
    def test_endor_max_retries_custom_value(self, mock_post) -> None:
        """Test ENDOR_MAX_RETRIES with custom value."""
        mock_response = Mock()
        mock_response.json.return_value = {"token": "test-token"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = APIClient()

        assert client.max_retries == 7
        assert client.session.adapters["https://"].max_retries.total == 7

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
    @patch("endorlabs.api_client.requests.post")
    def test_max_retries_default_when_env_not_set(self, mock_post) -> None:
        """Test default max_retries=5 when ENDOR_MAX_RETRIES not set."""
        mock_response = Mock()
        mock_response.json.return_value = {"token": "test-token"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = APIClient()

        assert client.max_retries == 5
        assert client.session.adapters["https://"].max_retries.total == 5

    @patch.dict(
        os.environ,
        {
            "ENDOR_API_CREDENTIALS_KEY": "test-key",
            "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
            "ENDOR_MAX_RETRIES": "3",
            "ENDOR_TOKEN": "",
            "ENDOR_AUTH_METHOD": "",
        },
        clear=True,
    )
    @patch("endorlabs.api_client.requests.post")
    def test_parameter_override_takes_precedence(self, mock_post) -> None:
        """Test that parameter override takes precedence over env var."""
        mock_response = Mock()
        mock_response.json.return_value = {"token": "test-token"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # ENDOR_MAX_RETRIES is set to 3, but we pass 10 explicitly
        client = APIClient(max_retries=10)

        assert client.max_retries == 10
        assert client.session.adapters["https://"].max_retries.total == 10


class TestEndorLogLevel:
    """Test ENDOR_LOG_LEVEL environment variable."""

    def test_endor_log_level_from_env(self) -> None:
        """Test that ENDOR_LOG_LEVEL environment variable is respected."""
        import logging

        # Reset logging to allow basicConfig to work
        logging.root.handlers = []
        logging.root.setLevel(logging.NOTSET)

        with patch.dict(os.environ, {"ENDOR_LOG_LEVEL": "DEBUG"}, clear=False):
            setup_logging("test_module")
            # Check root logger level (basicConfig sets root logger)
            assert logging.root.level == 10  # DEBUG level

    def test_endor_log_level_default_when_not_set(self) -> None:
        """Test default INFO level when ENDOR_LOG_LEVEL not set."""
        import logging

        # Reset logging to allow basicConfig to work
        logging.root.handlers = []
        logging.root.setLevel(logging.NOTSET)

        # Remove ENDOR_LOG_LEVEL if it exists
        env_backup = os.environ.pop("ENDOR_LOG_LEVEL", None)
        try:
            setup_logging("test_module")
            # Check root logger level
            assert logging.root.level == 20  # INFO level
        finally:
            if env_backup:
                os.environ["ENDOR_LOG_LEVEL"] = env_backup

    def test_endor_log_level_warning(self) -> None:
        """Test ENDOR_LOG_LEVEL with WARNING value."""
        import logging

        # Reset logging to allow basicConfig to work
        logging.root.handlers = []
        logging.root.setLevel(logging.NOTSET)

        with patch.dict(os.environ, {"ENDOR_LOG_LEVEL": "WARNING"}, clear=False):
            setup_logging("test_module")
            # Check root logger level
            assert logging.root.level == 30  # WARNING level

    def test_endor_log_level_error(self) -> None:
        """Test ENDOR_LOG_LEVEL with ERROR value."""
        import logging

        # Reset logging to allow basicConfig to work
        logging.root.handlers = []
        logging.root.setLevel(logging.NOTSET)

        with patch.dict(os.environ, {"ENDOR_LOG_LEVEL": "ERROR"}, clear=False):
            setup_logging("test_module")
            # Check root logger level
            assert logging.root.level == 40  # ERROR level


class TestClientSessionLogLevel:
    """Test that APIClient(logging_level=...) applies to all session loggers."""

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
    @patch("endorlabs.api_client.requests.post")
    def test_logging_level_applied_to_session_loggers(self, mock_post) -> None:
        """APIClient(logging_level='ERROR') sets session loggers to ERROR."""
        mock_response = Mock()
        mock_response.json.return_value = {"token": "test-token"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Save current levels so we don't affect other tests
        names = ("endorlabs", "urllib3", "requests")
        saved = {n: logging.getLogger(n).level for n in names}
        try:
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

        # Reset logging to allow basicConfig to work
        logging.root.handlers = []
        logging.root.setLevel(logging.NOTSET)

        # Set LOG_LEVEL but not ENDOR_LOG_LEVEL
        with patch.dict(
            os.environ,
            {"LOG_LEVEL": "DEBUG", "ENDOR_LOG_LEVEL": ""},
            clear=False,
        ):
            # Remove ENDOR_LOG_LEVEL if it exists
            env_backup = os.environ.pop("ENDOR_LOG_LEVEL", None)
            try:
                setup_logging("test_module")
                # Should default to INFO, not DEBUG
                assert logging.root.level == 20  # INFO level, not DEBUG (10)
            finally:
                if env_backup:
                    os.environ["ENDOR_LOG_LEVEL"] = env_backup

    def test_endor_log_level_takes_precedence_over_log_level(self) -> None:
        """Test that ENDOR_LOG_LEVEL takes precedence if both are set."""
        import logging

        # Reset logging to allow basicConfig to work
        logging.root.handlers = []
        logging.root.setLevel(logging.NOTSET)

        with patch.dict(
            os.environ,
            {"LOG_LEVEL": "DEBUG", "ENDOR_LOG_LEVEL": "WARNING"},
            clear=False,
        ):
            setup_logging("test_module")
            # Should use ENDOR_LOG_LEVEL (WARNING), not LOG_LEVEL (DEBUG)
            assert logging.root.level == 30  # WARNING level
