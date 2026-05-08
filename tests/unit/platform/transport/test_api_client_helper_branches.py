"""Branch coverage tests for APIClient helper methods."""

from __future__ import annotations

import pytest

from endorlabs.api_client import APIClient
from endorlabs.core.exceptions import ValidationError


def _client_for_helpers() -> APIClient:
    client = APIClient.__new__(APIClient)
    client.base_url = "https://api.endorlabs.com"
    client._allowed_api_hosts = {"api.endorlabs.com"}
    return client


def test_normalize_auth_method_alias_and_invalid() -> None:
    assert APIClient._normalize_auth_method("browser") == "browser-auth"
    assert APIClient._normalize_auth_method("api-key") == "api-key"
    assert APIClient._normalize_auth_method("not-a-method") == "not-a-method"


def test_build_allowed_hosts_normalizes_and_includes_base_host() -> None:
    client = _client_for_helpers()
    hosts = client._build_allowed_api_hosts(
        ["https://api.endorlabs.com", "example.com"]
    )
    assert "api.endorlabs.com" in hosts
    assert "example.com" in hosts


def test_validate_absolute_url_host_rejects_disallowed_host() -> None:
    client = _client_for_helpers()
    with pytest.raises(ValidationError, match="disallowed host"):
        client._validate_absolute_url_host("https://evil.example/v1/projects")


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"list": {"objects": [{"id": 1}]}}, [{"id": 1}]),
        ([{"id": 2}], [{"id": 2}]),
        ({"results": [{"id": 3}]}, []),
    ],
)
def test_extract_items_from_response_shapes(
    payload: object, expected: list[object]
) -> None:
    client = _client_for_helpers()
    assert client._extract_items_from_response(payload) == expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"list": {"response": {"next_page_token": "tok-1"}}}, "tok-1"),
        ({"nextPageToken": "tok-2"}, None),
        ({"items": []}, None),
    ],
)
def test_extract_next_page_token_fallbacks(
    payload: dict[str, object], expected: str | None
) -> None:
    client = _client_for_helpers()
    assert client._extract_next_page_token(payload) == expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"list": {"response": {"next_page_id": "id-1"}}}, "id-1"),
        ({"nextPageId": "id-2"}, None),
        ({"items": []}, None),
    ],
)
def test_extract_next_page_id_fallbacks(
    payload: dict[str, object], expected: str | None
) -> None:
    client = _client_for_helpers()
    assert client._extract_next_page_id(payload) == expected
