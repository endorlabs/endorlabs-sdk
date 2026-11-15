"""SDK-010 request observer hooks."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from endorlabs.api_client import APIClient

if TYPE_CHECKING:
    from endorlabs.core.observations import RequestObservation


class _Collector:
    def __init__(self) -> None:
        super().__init__()
        self.events: list[RequestObservation] = []

    def on_observation(self, observation: RequestObservation) -> None:
        self.events.append(observation)


def test_observer_sees_attempt_and_terminal(clear_auth_env: None) -> None:
    collector = _Collector()

    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("observer must not break caller")

    bad = MagicMock()
    bad.on_observation.side_effect = boom

    with patch.object(APIClient, "_ensure_fresh_token"):
        client = APIClient(
            token="test-token",
            request_observer=collector,
            observation_correlation={"run": "r1"},
        )

    resp = MagicMock()
    resp.status_code = 200
    resp.text = "{}"
    resp.json.return_value = {}
    client.client = MagicMock()
    client.client.request.return_value = resp
    with patch.object(client, "_handle_response", return_value=resp):
        out = client._request_with_retry("GET", "v1/auth")
    assert out is resp
    kinds = [e.kind for e in collector.events]
    assert "attempt" in kinds
    assert "terminal" in kinds
    assert collector.events[0].correlation == {"run": "r1"}

    # Observer failure does not change API success.
    client._request_observer = bad
    with patch.object(client, "_handle_response", return_value=resp):
        assert client._request_with_retry("GET", "v1/auth") is resp
    client.close()


@pytest.fixture
def clear_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "ENDOR_TOKEN",
        "ENDOR_API_CREDENTIALS_KEY",
        "ENDOR_API_CREDENTIALS_SECRET",
    ):
        monkeypatch.delenv(var, raising=False)
