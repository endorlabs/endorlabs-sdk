"""Tests for bearer token JWT expiration helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from endorlabs.utils.bearer_token import (
    expiration_from_auth_payload,
    expires_in_seconds,
    format_ttl_label,
    jwt_expiration_unverified,
    parse_iso_datetime,
    should_refresh_before_expiry,
)


def test_parse_iso_datetime_z_suffix() -> None:
    parsed = parse_iso_datetime("2026-07-03T02:18:05Z")
    assert parsed == datetime(2026, 7, 3, 2, 18, 5, tzinfo=UTC)


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


def test_expiration_from_auth_payload_iso() -> None:
    parsed = expiration_from_auth_payload({"expiration_time": "2026-07-05T00:39:52Z"})
    assert parsed == datetime(2026, 7, 5, 0, 39, 52, tzinfo=UTC)


def test_should_refresh_before_expiry() -> None:
    soon = datetime.now(UTC) + timedelta(minutes=10)
    assert should_refresh_before_expiry(soon, threshold_seconds=1800) is True
    later = datetime.now(UTC) + timedelta(hours=2)
    assert should_refresh_before_expiry(later, threshold_seconds=1800) is False


def test_expires_in_seconds_negative_when_past() -> None:
    past = datetime(2020, 1, 1, tzinfo=UTC)
    remaining = expires_in_seconds(past)
    assert remaining is not None
    assert remaining < 0


def test_format_ttl_label() -> None:
    assert format_ttl_label(0) == "expired"
    assert format_ttl_label(-1) == "expired"
    assert format_ttl_label(45) == "45s"
    assert format_ttl_label(125) == "2m 5s"
    assert format_ttl_label(7380) == "2h 3m"
