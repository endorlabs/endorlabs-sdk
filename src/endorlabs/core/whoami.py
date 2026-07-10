"""Structured identity + session metadata from ``Client.whoami()``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast, override


def identity_from_auth_payload(payload: dict[str, object]) -> str | None:
    """Extract email / username / meta.name from a ``GET /v1/auth`` body."""
    user = payload.get("user")
    if not isinstance(user, dict):
        return None
    user_dict = cast("dict[str, object]", user)
    spec = user_dict.get("spec")
    if isinstance(spec, dict):
        spec_dict = cast("dict[str, object]", spec)
        for key in ("email", "user_name"):
            value = spec_dict.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    meta = user_dict.get("meta")
    if isinstance(meta, dict):
        meta_dict = cast("dict[str, object]", meta)
        name = meta_dict.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


@dataclass(frozen=True)
class WhoamiResult:
    """Identity and optional bearer session metadata from ``/v1/auth`` or JWT."""

    identity: str | None
    authentication_source: str | None = None
    expiration_time: datetime | None = None
    expires_in_seconds: float | None = None
    is_expired: bool | None = None
    auth_type: Literal["api-key", "browser"] | None = None
    expiration_source: Literal["v1_auth", "jwt", "api_key_exchange"] | None = None

    @override
    def __str__(self) -> str:
        return self.identity or ""

    def __bool__(self) -> bool:
        """True when ``identity`` is non-empty."""
        return bool(self.identity)

    @override
    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.identity == other
        if isinstance(other, WhoamiResult):
            return self.identity == other.identity
        return NotImplemented

    @override
    def __hash__(self) -> int:
        return hash(self.identity)
