"""API key token lifecycle tests (transport layer)."""

from collections.abc import Callable
from datetime import UTC, datetime

import httpx

from endorlabs.api_client import APIClient


class _FakeResponse:
    def __init__(
        self,
        *,
        payload: dict[str, object] | None = None,
        status_code: int = 200,
        request_url: str = "https://api.endorlabs.com/v1/auth/api-key",
    ) -> None:
        super().__init__()
        self._payload = payload or {}
        self.status_code = status_code
        self.request = httpx.Request("POST", request_url)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "auth error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self) -> dict[str, object]:
        return self._payload


class _StubHttpClient:
    def __init__(
        self,
        post_handler: Callable[[int], _FakeResponse],
        *args: object,
        get_handler: Callable[[], _FakeResponse] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__()
        del args, kwargs
        self._post_handler = post_handler
        self._get_handler = get_handler
        self.post_calls = 0
        self.get_calls = 0

    @property
    def calls(self) -> int:
        """Backward-compatible POST call count."""
        return self.post_calls

    def post(self, *args: object, **kwargs: object) -> _FakeResponse:
        del args, kwargs
        self.post_calls += 1
        return self._post_handler(self.post_calls)

    def get(self, *args: object, **kwargs: object) -> _FakeResponse:
        del args, kwargs
        self.get_calls += 1
        if self._get_handler is not None:
            return self._get_handler()
        return _FakeResponse(
            payload={},
            request_url="https://api.endorlabs.com/v1/auth",
        )

    def close(self) -> None:
        return


def test_token_does_not_reauthenticate_when_expiry_is_unknown(
    monkeypatch,
) -> None:
    fake_holder: dict[str, _StubHttpClient] = {}

    def _post_handler(_call_no: int) -> _FakeResponse:
        return _FakeResponse(payload={"token": "token-1"})

    def _get_handler() -> _FakeResponse:
        return _FakeResponse(
            payload={"expiration_time": "2099-01-01T00:00:00Z"},
            request_url="https://api.endorlabs.com/v1/auth",
        )

    def _factory(*args: object, **kwargs: object) -> _StubHttpClient:
        fake = _StubHttpClient(_post_handler, *args, get_handler=_get_handler, **kwargs)
        fake_holder["client"] = fake
        return fake

    monkeypatch.setattr("endorlabs.api_client.httpx.Client", _factory)
    monkeypatch.delenv("ENDOR_TOKEN", raising=False)
    client = APIClient(
        key="test-key",
        secret="test-secret",
        base_url="https://api.endorlabs.com",
    )
    try:
        assert client.token == "token-1"
        assert client.token == "token-1"
        assert fake_holder["client"].post_calls == 1
        assert fake_holder["client"].get_calls == 1
    finally:
        client.close()


def test_api_key_auth_retries_transient_connect_error(monkeypatch) -> None:
    request = httpx.Request("POST", "https://api.endorlabs.com/v1/auth/api-key")
    fake_holder: dict[str, _StubHttpClient] = {}

    def _post_handler(call_no: int) -> _FakeResponse:
        if call_no == 2:
            raise httpx.ConnectError("connection dropped", request=request)
        return _FakeResponse(payload={"token": "token-2", "expiresIn": 1200})

    def _factory(*args: object, **kwargs: object) -> _StubHttpClient:
        fake = _StubHttpClient(_post_handler, *args, **kwargs)
        fake_holder["client"] = fake
        return fake

    monkeypatch.setattr("endorlabs.api_client.httpx.Client", _factory)
    monkeypatch.setattr("endorlabs.api_client.time.sleep", lambda _seconds: None)

    client = APIClient(
        key="test-key",
        secret="test-secret",
        base_url="https://api.endorlabs.com",
    )
    try:
        initial_calls = fake_holder["client"].post_calls
        client._token = None
        token = client._authenticate_api_key()
        assert token == "token-2"
        assert fake_holder["client"].post_calls - initial_calls == 2
        assert client._token_expires is not None
        assert client._token_expires > datetime.now(UTC)
    finally:
        client.close()
