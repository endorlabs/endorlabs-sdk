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

    def test_429_raises_for_retry_loop(self, authed_client: APIClient) -> None:
        response = _response(429, headers={"Retry-After": "3"})

        with pytest.raises(httpx.HTTPStatusError):
            authed_client._handle_response(response, method="GET", url="/v1/projects")

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

    def test_401_reauth_via_get_uses_fresh_token_on_second_request(
        self,
        authed_client: APIClient,
    ) -> None:
        first = _response(401, text="Unauthorized")
        second = _response(200, text='{"ok":true}')
        assert authed_client.client is not None
        authed_client.client.request.side_effect = [first, second]

        with patch.object(authed_client, "authenticate", return_value="NEW_TOKEN"):
            result = authed_client.get("/v1/projects")

        assert result.status_code == 200
        assert authed_client.client.request.call_count == 2
        second_headers = authed_client.client.request.call_args_list[1].kwargs[
            "headers"
        ]
        assert second_headers["Authorization"] == "Bearer NEW_TOKEN"

    def test_429_retry_uses_retry_after_header(
        self,
        authed_client: APIClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        assert authed_client.client is not None
        rate_limited = _response(429, headers={"Retry-After": "30"})
        success = _response(200, text='{"ok":true}')
        authed_client.client.request.side_effect = [rate_limited, success]
        authed_client.max_retries = 1

        sleeps: list[float] = []

        def _record_sleep(seconds: float) -> None:
            sleeps.append(seconds)

        monkeypatch.setattr("endorlabs.api_client.time.sleep", _record_sleep)

        result = authed_client._request_with_retry("GET", "/v1/projects")

        assert result.status_code == 200
        assert sleeps[0] >= 30.0
        assert sleeps[0] <= 60.0

    def test_429_retry_after_capped_at_sixty_seconds(
        self,
        authed_client: APIClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        assert authed_client.client is not None
        rate_limited = _response(429, headers={"Retry-After": "120"})
        success = _response(200, text='{"ok":true}')
        authed_client.client.request.side_effect = [rate_limited, success]
        authed_client.max_retries = 1

        sleeps: list[float] = []

        def _record_sleep(seconds: float) -> None:
            sleeps.append(seconds)

        monkeypatch.setattr("endorlabs.api_client.time.sleep", _record_sleep)

        authed_client._request_with_retry("GET", "/v1/projects")

        assert sleeps == [60.0]

    def test_concurrent_401_triggers_single_authenticate(
        self,
        authed_client: APIClient,
    ) -> None:
        import threading
        import time

        assert authed_client.client is not None
        auth_calls: list[int] = []

        def _slow_api_key_auth(self: APIClient) -> str | None:
            auth_calls.append(1)
            time.sleep(0.05)
            self._apply_session_token("NEW_TOKEN")
            return "NEW_TOKEN"

        first = _response(401, text="Unauthorized")
        second = _response(200, text='{"ok":true}')
        authed_client.client.request.side_effect = [first, first, second, second]

        with patch.object(APIClient, "_authenticate_api_key", _slow_api_key_auth):
            results: list[int] = []
            barrier = threading.Barrier(2)

            def _worker() -> None:
                barrier.wait()
                response = authed_client.get("/v1/projects")
                results.append(response.status_code)

            threads = [threading.Thread(target=_worker) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5.0)

        assert results == [200, 200]
        assert len(auth_calls) == 1
