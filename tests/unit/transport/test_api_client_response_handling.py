"""Characterization tests for APIClient _handle_response status handling."""

import os
from collections.abc import Iterator
from unittest.mock import Mock, patch

import httpx
import pytest

from endorlabs.api_client import APIClient


def _response(
    status_code: int,
    *,
    url: str = "https://api.endorlabs.com/v1/namespaces/test/projects",
    headers: dict[str, str] | None = None,
    text: str = "error",
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        headers=headers,
        text=text,
        request=httpx.Request("GET", url),
    )


def _auth_success_response(token: str = "init-token") -> httpx.Response:
    return httpx.Response(
        status_code=200,
        json={"token": token},
        request=httpx.Request("POST", "https://api.endorlabs.com/v1/auth/api-key"),
    )


@pytest.fixture
def authed_client() -> Iterator[APIClient]:
    """Build APIClient with mocked httpx transport and auth success."""
    with (
        patch.dict(
            os.environ,
            {
                "ENDOR_API_CREDENTIALS_KEY": "test-key",
                "ENDOR_API_CREDENTIALS_SECRET": "test-secret",
                "ENDOR_TOKEN": "",
                "ENDOR_AUTH_METHOD": "",
            },
            clear=True,
        ),
        patch("endorlabs.api_client.httpx.Client") as mock_http_client_cls,
    ):
        mock_http = Mock()
        mock_http.post.return_value = _auth_success_response()
        mock_http_client_cls.return_value = mock_http
        client = APIClient()
        yield client


class TestAPIClientResponseHandling:
    """Characterization tests for status-class specific behavior."""

    def test_429_sets_rate_limit_delay_and_raises(
        self,
        authed_client: APIClient,
    ) -> None:
        response = _response(429, headers={"Retry-After": "3"})

        with pytest.raises(httpx.HTTPStatusError):
            authed_client._handle_response(response, method="GET", url="/v1/projects")

        assert authed_client.rate_limit_delay == 4

    def test_400_raises_http_status_error(self, authed_client: APIClient) -> None:
        response = _response(400)
        with pytest.raises(httpx.HTTPStatusError):
            authed_client._handle_response(response, method="GET", url="/v1/projects")

    def test_501_raises_http_status_error(self, authed_client: APIClient) -> None:
        response = _response(501)
        with pytest.raises(httpx.HTTPStatusError):
            authed_client._handle_response(response, method="POST", url="/v1/projects")

    def test_5xx_raises_http_status_error(self, authed_client: APIClient) -> None:
        response = _response(503)
        with pytest.raises(httpx.HTTPStatusError):
            authed_client._handle_response(response, method="GET", url="/v1/projects")

    def test_401_reauth_retries_once_and_succeeds(
        self,
        authed_client: APIClient,
    ) -> None:
        first = _response(401, text="Unauthorized")
        second = _response(200, text='{"ok":true}')
        assert authed_client.client is not None
        authed_client.client.request.return_value = second

        with patch.object(authed_client, "authenticate", return_value="new-token"):
            result = authed_client._handle_response(
                first,
                method="GET",
                url="/v1/projects",
            )

        assert result.status_code == 200
        assert authed_client.default_headers["Authorization"] == "Bearer new-token"
