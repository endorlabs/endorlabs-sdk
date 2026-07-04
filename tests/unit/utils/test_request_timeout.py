"""Tests for shared request timeout resolution."""

from __future__ import annotations

import os
from unittest.mock import patch

from endorlabs.utils.request_timeout import (
    DEFAULT_REQUEST_TIMEOUT,
    resolve_create_timeout,
    resolve_request_timeout,
)


class TestResolveRequestTimeout:
    @patch.dict(os.environ, {}, clear=True)
    def test_default_when_unset(self) -> None:
        assert resolve_request_timeout(None) == DEFAULT_REQUEST_TIMEOUT

    @patch.dict(os.environ, {"ENDOR_REQUEST_TIMEOUT": "120"}, clear=True)
    def test_endor_request_timeout(self) -> None:
        assert resolve_request_timeout(None) == 120.0

    @patch.dict(os.environ, {"ENDOR_API_TIMEOUT": "20"}, clear=True)
    def test_endor_api_timeout_fallback(self) -> None:
        assert resolve_request_timeout(None) == 20.0

    @patch.dict(
        os.environ,
        {"ENDOR_REQUEST_TIMEOUT": "90", "ENDOR_API_TIMEOUT": "20"},
        clear=True,
    )
    def test_request_timeout_precedes_api_timeout(self) -> None:
        assert resolve_request_timeout(None) == 90.0

    @patch.dict(os.environ, {"ENDOR_REQUEST_TIMEOUT": "120"}, clear=True)
    def test_explicit_overrides_env(self) -> None:
        assert resolve_request_timeout(45.0) == 45.0

    @patch.dict(os.environ, {}, clear=True)
    def test_custom_default(self) -> None:
        assert resolve_request_timeout(None, default=900.0) == 900.0


class TestResolveCreateTimeout:
    @patch.dict(os.environ, {}, clear=True)
    def test_none_when_unset(self) -> None:
        assert resolve_create_timeout() is None

    @patch.dict(os.environ, {"ENDOR_CREATE_TIMEOUT": "90"}, clear=True)
    def test_from_env(self) -> None:
        assert resolve_create_timeout() == 90.0

    @patch.dict(os.environ, {"ENDOR_CREATE_TIMEOUT": "not-a-number"}, clear=True)
    def test_invalid_env_returns_none(self) -> None:
        assert resolve_create_timeout() is None
