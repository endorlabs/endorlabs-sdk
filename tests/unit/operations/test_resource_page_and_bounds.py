"""Tests for public ResourcePage bounds and host deadline/cancel (SDK-002/003)."""

from __future__ import annotations

import threading
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from endorlabs.api_client import APIClient
from endorlabs.core.credentials import ApiKeyCredentials, BearerCredentials
from endorlabs.core.exceptions import DeadlineExceededError, RequestCancelledError
from endorlabs.operations.pagination import (
    PageCursor,
    PaginationBound,
    completeness_for_stop,
    iter_paginated_pages,
)


@pytest.fixture
def clear_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "ENDOR_TOKEN",
        "ENDOR_API_CREDENTIALS_KEY",
        "ENDOR_API_CREDENTIALS_SECRET",
    ):
        monkeypatch.delenv(var, raising=False)


def test_completeness_for_stop_mapping() -> None:
    assert completeness_for_stop("complete", had_next_cursor=False) == "complete"
    assert completeness_for_stop("max_pages", had_next_cursor=True) == "capped"
    assert completeness_for_stop("max_items", had_next_cursor=True) == "capped"
    assert completeness_for_stop("cancelled", had_next_cursor=True) == "unknown"
    assert completeness_for_stop("deadline", had_next_cursor=False) == "unknown"


def test_iter_paginated_pages_records_max_items_stop() -> None:
    def fetch_page(cursor: PageCursor | None) -> dict[str, Any]:
        if cursor is None:
            return {"n": 1, "items": [1, 2]}
        return {"n": 2, "items": [3, 4]}

    def next_cursor(page: dict[str, Any]) -> PageCursor | None:
        if page["n"] == 1:
            return PageCursor(page_token="t2")
        return None

    bound = PaginationBound(max_items=3)
    pages = list(
        iter_paginated_pages(
            fetch_page,
            next_cursor=next_cursor,
            bound=bound,
            extract_items=lambda p: p["items"],
            label="items",
        )
    )
    assert len(pages) == 2
    assert bound.stop_reason == "max_items"
    assert bound.items_fetched >= 3


def test_api_client_cancel_event_blocks_request(clear_auth_env: None) -> None:
    event = threading.Event()
    event.set()
    client = APIClient(cancel_event=event)
    with pytest.raises(RequestCancelledError, match="cancel_event"):
        client._raise_if_host_budget_exceeded()
    client.close()


def test_api_client_deadline_blocks_request(clear_auth_env: None) -> None:
    client = APIClient(deadline_seconds=0.0)
    with pytest.raises(DeadlineExceededError, match="deadline_seconds"):
        client._raise_if_host_budget_exceeded()
    client.close()


def test_api_client_does_not_close_injected_http_client(
    clear_auth_env: None,
) -> None:
    http = MagicMock(spec=httpx.Client)
    client = APIClient(http_client=http)
    client.close()
    http.close.assert_not_called()


def test_credential_provider_bearer_applied(clear_auth_env: None) -> None:
    class Prov:
        def resolve(self) -> BearerCredentials:
            return BearerCredentials(token="provider-token")

    with patch.object(APIClient, "_ensure_fresh_token"):
        client = APIClient(credential_provider=Prov())
    assert client._provided_token == "provider-token"
    assert client._auth_type == "browser"
    client.close()


def test_credential_provider_api_key_applied(clear_auth_env: None) -> None:
    class Prov:
        def resolve(self) -> ApiKeyCredentials:
            return ApiKeyCredentials(key="k", secret="s")

    with patch.object(APIClient, "_ensure_fresh_token"):
        client = APIClient(credential_provider=Prov())
    assert client.key == "k"
    assert client.secret == "s"
    assert client._auth_type == "api-key"
    client.close()


def test_iter_pages_terminal_metadata(
    monkeypatch: pytest.MonkeyPatch, clear_auth_env: None
) -> None:
    with patch.object(APIClient, "_ensure_fresh_token"):
        client = APIClient(token="test-token")
    pages_payload = [
        {
            "list": {
                "objects": [{"uuid": "a"}, {"uuid": "b"}],
                "response": {"next_page_id": "p2"},
            }
        },
        {
            "list": {
                "objects": [{"uuid": "c"}],
                "response": {},
            }
        },
    ]
    state = {"i": 0}

    def fake_get(url: str, **kwargs: Any) -> Any:
        resp = MagicMock()
        resp.json.return_value = pages_payload[state["i"]]
        state["i"] += 1
        resp.status_code = 200
        return resp

    monkeypatch.setattr(client, "get", fake_get)
    monkeypatch.setattr(client, "_ensure_authenticated", lambda: None)
    monkeypatch.setattr(client, "_raise_if_host_budget_exceeded", lambda: None)

    pages = list(
        client.iter_pages(
            "v1/namespaces/example-tenant/projects",
            owner_namespace="example-tenant",
            requested_page_size=2,
        )
    )
    assert len(pages) == 2
    assert pages[0].stop_reason is None
    assert pages[0].completeness == "unknown"
    assert pages[0].next_cursor is not None
    assert pages[1].stop_reason == "complete"
    assert pages[1].completeness == "complete"
    assert [i["uuid"] for i in pages[1].items] == ["c"]
    client.close()
