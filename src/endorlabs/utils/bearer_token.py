"""Bearer token expiration helpers (JWT decode without signature verification)."""

from __future__ import annotations

import base64
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any


def parse_iso_datetime(raw: str) -> datetime | None:
    """Parse RFC3339 / ISO datetime strings from API payloads."""
    try:
        normalized = re.sub(r"\s*Z$", "+00:00", raw.strip())
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except ValueError:
        return None


def jwt_payload_unverified(token: str) -> dict[str, Any] | None:
    """Decode JWT payload without verifying signature."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload_b64 = parts[1]
    pad = "=" * (-len(payload_b64) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload_b64 + pad)
        parsed = json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def jwt_expiration_unverified(token: str) -> datetime | None:
    """Return JWT ``exp`` claim as UTC datetime when present."""
    payload = jwt_payload_unverified(token)
    if payload is None:
        return None
    exp = payload.get("exp")
    if isinstance(exp, (int, float)):
        return datetime.fromtimestamp(exp, tz=UTC)
    return None


def expires_in_seconds(expiration: datetime | None) -> float | None:
    """Seconds until *expiration* (negative when already expired)."""
    if expiration is None:
        return None
    exp = expiration.replace(tzinfo=UTC) if expiration.tzinfo is None else expiration
    return (exp - datetime.now(UTC)).total_seconds()


def expiration_from_auth_payload(payload: dict[str, Any]) -> datetime | None:
    """Parse ``expiration_time`` / ``expirationTime`` from auth API payloads."""
    for key in ("expiration_time", "expirationTime"):
        raw = payload.get(key)
        if isinstance(raw, str) and raw.strip():
            parsed = parse_iso_datetime(raw)
            if parsed is not None:
                return parsed
    for key in ("expiresIn", "expires_in", "ttl", "ttl_seconds"):
        raw = payload.get(key)
        if isinstance(raw, (int, float)):
            return datetime.now(UTC) + timedelta(seconds=max(0.0, float(raw)))
        if isinstance(raw, str):
            match = re.match(r"^(\d+(?:\.\d+)?)\s*s?$", raw.strip(), re.IGNORECASE)
            if match:
                return datetime.now(UTC) + timedelta(seconds=float(match.group(1)))
    return None


def resolve_token_expiration(
    token: str,
    *,
    auth_payload: dict[str, Any] | None = None,
) -> tuple[datetime | None, str | None]:
    """Resolve expiry: prefer server auth payload, else unverified JWT ``exp``."""
    if auth_payload is not None:
        server_exp = expiration_from_auth_payload(auth_payload)
        if server_exp is not None:
            return server_exp, "v1_auth"
    jwt_exp = jwt_expiration_unverified(token)
    if jwt_exp is not None:
        return jwt_exp, "jwt"
    return None, None


def should_refresh_before_expiry(
    expiration: datetime | None,
    *,
    threshold_seconds: float,
) -> bool:
    """True when *expiration* is within *threshold_seconds* (or already past)."""
    remaining = expires_in_seconds(expiration)
    if remaining is None:
        return False
    return remaining <= threshold_seconds
