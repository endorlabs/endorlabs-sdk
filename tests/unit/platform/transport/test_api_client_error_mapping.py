"""Tests for APIClient HTTP error mapping and transport failure wrapping."""

from __future__ import annotations

import os
from collections.abc import Iterator
from unittest.mock import Mock, patch

import httpx
import pytest

from endorlabs.api_client import APIClient
from endorlabs.core.exceptions import NetworkError, NotFoundError, ServerError


def _http_status_error(
    status_code: int,
    *,
    json_body: dict[str, object] | None = None,
    text: str = "",
) -> httpx.HTTPStatusError:
    request = httpx.Request(
        "GET",
        "https://api.endorlabs.com/v1/namespaces/tenant.ns/findings",
    )
    if json_body is not None:
        response = httpx.Response(status_code, json=json_body, request=request)
    else:
        response = httpx.Response(status_code, text=text, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


def _client_for_mapping() -> APIClient:
    client = APIClient.__new__(APIClient)
    client.base_url = "https://api.endorlabs.com"
    return client


def test_map_http_error_uses_grpc_hint_when_body_generic() -> None:
    client = _client_for_mapping()
    error = _http_status_error(
        504,
        json_body={"code": 4, "message": "HTTP 504 error"},
    )

    exc = client.map_http_error_to_exception(error, "list", "tenant.ns")

    assert isinstance(exc, ServerError)
    assert "pagination" in exc.message.lower()


def test_map_http_error_preserves_specific_server_message() -> None:
    client = _client_for_mapping()
    specific = "Invalid filter path: 'spec.not_a_field'"
    error = _http_status_error(
        400,
        json_body={"code": 3, "message": "invalid path 'spec.not_a_field'"},
    )

    exc = client.map_http_error_to_exception(error, "list", "tenant.ns")

    assert specific in exc.message


def test_map_http_error_404_list_appends_namespace_hint() -> None:
    client = _client_for_mapping()
    error = _http_status_error(
        404,
        json_body={"code": 5, "message": "Resource not found"},
    )

    exc = client.map_http_error_to_exception(error, "list", "tenant.ns")

    assert isinstance(exc, NotFoundError)
    assert "endor-namespace-scoping" in exc.message


@pytest.fixture
def authed_client() -> Iterator[APIClient]:
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
        patch("endorlabs.api_client.httpx.Client") as mock_http_client_cls,
    ):
        mock_http = Mock()
        mock_http.post.return_value = httpx.Response(
            status_code=200,
            json={"token": "init-token"},
            request=httpx.Request("POST", "https://api.endorlabs.com/v1/auth/api-key"),
        )
        mock_http_client_cls.return_value = mock_http
        client = APIClient(max_retries=0)
        yield client
        client.close()


def test_request_with_retry_raises_network_error(authed_client: APIClient) -> None:
    request = httpx.Request("GET", "https://api.endorlabs.com/v1/namespaces/t/x")
    assert authed_client.client is not None
    authed_client.client.request.side_effect = httpx.ConnectError(
        "connection dropped",
        request=request,
    )

    with pytest.raises(NetworkError, match="Network error after"):
        authed_client._request_with_retry("GET", "/v1/namespaces/t/x")
