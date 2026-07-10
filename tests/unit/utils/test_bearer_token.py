"""Tests for bearer token JWT expiration helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from endorlabs.utils.bearer_token import (
    format_ttl_label,
    jwt_expiration_unverified,
)


def test_jwt_expiration_unverified_extracts_exp() -> None:
    # header.payload.sig — payload {"exp": 1783045085}
    import base64
    import json

    payload = (
        base64.urlsafe_b64encode(json.dumps({"exp": 1783045085}).encode())
        .decode()
        .rstrip("=")
    )
    token = f"aaa.{payload}.bbb"
    exp = jwt_expiration_unverified(token)
    assert exp == datetime.fromtimestamp(1783045085, tz=UTC)


def test_format_ttl_label() -> None:
    assert format_ttl_label(0) == "expired"
    assert format_ttl_label(-1) == "expired"
    assert format_ttl_label(45) == "45s"
    assert format_ttl_label(125) == "2m 5s"
    assert format_ttl_label(7380) == "2h 3m"
