"""ClientIdentity factories and APIClient identity header wiring."""

from __future__ import annotations

import os
from unittest.mock import Mock, patch

import httpx
import pytest

from endorlabs.api_client import APIClient
from endorlabs.core.client_identity import (
    CALLER_SDK,
    ClientIdentity,
    sdk_package_version,
)


def _make_auth_response_mock(token: str = "test-token") -> Mock:
    mock_response = Mock()
    mock_response.json.return_value = {"token": token}
    mock_response.raise_for_status = Mock()
    mock_response.status_code = 200
    mock_response.text = ""
    mock_response.url = "https://api.endorlabs.com/v1/auth/api-key"
    mock_response.headers = {}
    return mock_response


def _patch_httpx_client_for_auth() -> Mock:
    mock_http = Mock()
    mock_http.post.return_value = _make_auth_response_mock()
    mock_http.get.return_value = _make_auth_response_mock()
    mock_http.headers = httpx.Headers()
    return patch("endorlabs.api_client.httpx.Client", return_value=mock_http)


_AUTH_ENV = {
    "ENDOR_API_CREDENTIALS_KEY": "test-key",
    "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
    "ENDOR_TOKEN": "",
}


class TestClientIdentityFactories:
    def test_sdk_defaults(self) -> None:
        identity = ClientIdentity.sdk()
        ver = sdk_package_version()
        assert identity.caller == CALLER_SDK
        assert identity.caller_version == ver
        assert identity.user_agent == f"{CALLER_SDK}/{ver}"
        assert identity.op_comment is None
        assert identity.as_headers()["User-Agent"] == identity.user_agent
        assert identity.as_headers()["x-endor-caller"] == CALLER_SDK

    def test_workflow_sets_op_comment(self) -> None:
        identity = ClientIdentity.workflow("endor-reports")
        ver = sdk_package_version()
        assert identity.op_comment == f"endor-reports/{ver}"
        assert identity.as_headers()["x-endor-op-comment"] == identity.op_comment

    def test_custom_host_plane(self) -> None:
        identity = ClientIdentity.custom(
            caller="my-host",
            caller_version="1.0.0",
            user_agent="my-host/1.0.0 endorlabs-sdk/0.7.5",
        )
        assert identity.caller == "my-host"
        assert identity.as_headers()["x-endor-caller-version"] == "1.0.0"
        assert identity.user_agent.startswith("my-host/")

    def test_rejects_endorctl_op_comment(self) -> None:
        with pytest.raises(ValueError, match="endorctl"):
            ClientIdentity.sdk(op_comment="service/endorctl")

    def test_rejects_forged_endorctl_caller(self) -> None:
        with pytest.raises(ValueError, match="endorctl"):
            ClientIdentity(
                caller="endorctl",
                caller_version="1",
                user_agent="endorctl/1",
            )


class TestAPIClientIdentityHeaders:
    @patch.dict(os.environ, _AUTH_ENV, clear=True)
    def test_default_sdk_identity_headers(self) -> None:
        with _patch_httpx_client_for_auth():
            client = APIClient()
        ver = sdk_package_version()
        assert client._request_headers["User-Agent"] == f"{CALLER_SDK}/{ver}"
        assert client._request_headers["x-endor-caller"] == CALLER_SDK
        assert client._request_headers["x-endor-caller-version"] == ver

    @patch.dict(os.environ, _AUTH_ENV, clear=True)
    def test_op_comment_kwarg_overrides_identity(self) -> None:
        with _patch_httpx_client_for_auth():
            client = APIClient(
                identity=ClientIdentity.sdk(op_comment="old/1"),
                op_comment="endor-reports/9.9.9",
            )
        assert client._request_headers["x-endor-op-comment"] == "endor-reports/9.9.9"

    @patch.dict(os.environ, _AUTH_ENV, clear=True)
    def test_injected_http_client_preserves_user_agent(self) -> None:
        injected = Mock()
        injected.headers = httpx.Headers({"User-Agent": "host-custom/1.0"})
        with patch.object(APIClient, "_has_configured_credentials", return_value=False):
            client = APIClient(http_client=injected)
        assert "User-Agent" not in client._request_headers
        assert client._request_headers["x-endor-caller"] == CALLER_SDK
        assert "x-endor-caller-version" in client._request_headers
        client.close()
