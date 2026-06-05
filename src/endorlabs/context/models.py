"""Models for context bootstrap functionality."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import override


@dataclass
class InitStatus:
    """Status returned by endorlabs.init() after context bootstrap.

    Attributes:
        agent_bundle_path: Materialized SDK agent bundle under context (sdk/).
        context_json_path: Path to context.json init manifest.
        platform_openapi_path: Path to downloaded OpenAPI spec (None if skipped).
        platform_user_docs_path: Path to user docs directory (None if skipped).
        openapi_path: Backward-compatible alias for platform_openapi_path.
        user_docs_path: Backward-compatible alias for platform_user_docs_path.
        user_docs_count: Number of user doc pages downloaded.
        synced_skill_paths: Runtime skill mirrors refreshed during bootstrap.
        downloaded_at: Timestamp when bootstrap completed.

    """

    agent_bundle_path: Path | None
    context_json_path: Path | None
    platform_openapi_path: Path | None
    platform_user_docs_path: Path | None
    user_docs_count: int
    downloaded_at: datetime
    synced_skill_paths: dict[str, Path] = field(default_factory=dict)

    @property
    def openapi_path(self) -> Path | None:
        """Backward-compatible alias for platform OpenAPI path."""
        return self.platform_openapi_path

    @property
    def user_docs_path(self) -> Path | None:
        """Backward-compatible alias for platform user docs path."""
        return self.platform_user_docs_path

    @property
    def agent_index_path(self) -> Path | None:
        """Tier-0 INDEX.md inside the materialized agent bundle."""
        if self.agent_bundle_path is None:
            return None
        return self.agent_bundle_path / "INDEX.md"

    @override
    def __repr__(self) -> str:
        """Return string representation of InitStatus."""
        parts = [f"InitStatus(downloaded_at={self.downloaded_at.isoformat()!r}"]
        if self.agent_bundle_path:
            parts.append(f"agent_bundle_path={self.agent_bundle_path!r}")
        if self.context_json_path:
            parts.append(f"context_json_path={self.context_json_path!r}")
        if self.platform_openapi_path:
            parts.append(f"platform_openapi_path={self.platform_openapi_path!r}")
        if self.platform_user_docs_path:
            parts.append(f"platform_user_docs_path={self.platform_user_docs_path!r}")
            parts.append(f"user_docs_count={self.user_docs_count}")
        if self.synced_skill_paths:
            parts.append(f"synced_skill_paths={self.synced_skill_paths!r}")
        return ", ".join(parts) + ")"
