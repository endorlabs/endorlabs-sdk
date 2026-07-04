"""Shared HTTP timeout resolution for Client and APIClient."""

from __future__ import annotations

import os

DEFAULT_REQUEST_TIMEOUT: float = 60.0


def resolve_request_timeout(
    explicit: float | None = None,
    *,
    default: float = DEFAULT_REQUEST_TIMEOUT,
) -> float:
    """Resolve read timeout: arg, then env vars, then *default*."""
    if explicit is not None:
        return float(explicit)
    env_timeout = os.getenv("ENDOR_REQUEST_TIMEOUT")
    if env_timeout:
        return float(env_timeout)
    api_timeout = os.getenv("ENDOR_API_TIMEOUT")
    if api_timeout:
        return float(api_timeout)
    return default


def resolve_create_timeout(explicit: int | float | None = None) -> float | None:
    """Resolve create POST timeout from arg or ENDOR_CREATE_TIMEOUT."""
    if explicit is not None:
        return float(explicit)
    env_timeout = os.environ.get("ENDOR_CREATE_TIMEOUT")
    if env_timeout is None:
        return None
    try:
        return float(env_timeout)
    except ValueError:
        return None
