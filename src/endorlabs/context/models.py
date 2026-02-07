"""Models for context bootstrap functionality."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import override


@dataclass
class InitStatus:
    """Status returned by endorlabs.init() after context bootstrap.

    Attributes:
        openapi_path: Path to downloaded OpenAPI spec (None if not downloaded).
        user_docs_path: Path to user docs directory (None if not downloaded).
        user_docs_count: Number of user doc pages downloaded.
        downloaded_at: Timestamp when download completed.

    """

    openapi_path: Path | None
    user_docs_path: Path | None
    user_docs_count: int
    downloaded_at: datetime

    @override
    def __repr__(self) -> str:
        """Return string representation of InitStatus."""
        parts = [f"InitStatus(downloaded_at={self.downloaded_at.isoformat()!r}"]
        if self.openapi_path:
            parts.append(f"openapi_path={self.openapi_path!r}")
        if self.user_docs_path:
            parts.append(f"user_docs_path={self.user_docs_path!r}")
            parts.append(f"user_docs_count={self.user_docs_count}")
        return ", ".join(parts) + ")"
