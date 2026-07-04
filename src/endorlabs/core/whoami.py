"""Structured identity + session metadata from ``Client.whoami()``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, override


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
