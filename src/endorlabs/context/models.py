"""Models for context bootstrap functionality."""

from dataclasses import dataclass, field
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
        synced_skill_paths: Runtime skill mirrors refreshed during bootstrap.
        downloaded_at: Timestamp when download completed.

    """

    openapi_path: Path | None
    user_docs_path: Path | None
    user_docs_count: int
    downloaded_at: datetime
    synced_skill_paths: dict[str, Path] = field(default_factory=dict)

    @override
    def __repr__(self) -> str:
        """Return string representation of InitStatus."""
        parts = [f"InitStatus(downloaded_at={self.downloaded_at.isoformat()!r}"]
        if self.openapi_path:
            parts.append(f"openapi_path={self.openapi_path!r}")
        if self.user_docs_path:
            parts.append(f"user_docs_path={self.user_docs_path!r}")
            parts.append(f"user_docs_count={self.user_docs_count}")
        if self.synced_skill_paths:
            parts.append(f"synced_skill_paths={self.synced_skill_paths!r}")
        return ", ".join(parts) + ")"
