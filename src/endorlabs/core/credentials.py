"""Host-injectable credential resolution (SDK-003).

Providers return credentials without requiring process-environment mutation.
``None`` from ``resolve()`` means no credentials available yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class BearerCredentials:
    """Bearer / browser-session token."""

    token: str


@dataclass(frozen=True, slots=True)
class ApiKeyCredentials:
    """API key + secret pair."""

    key: str
    secret: str


Credentials = BearerCredentials | ApiKeyCredentials


@runtime_checkable
class CredentialProvider(Protocol):
    """Resolve credentials for APIClient authentication."""

    def resolve(self) -> Credentials | None:
        """Return current credentials, or ``None`` if unavailable."""
        ...
