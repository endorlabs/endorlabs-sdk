"""Models for context bootstrap functionality."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import override


@dataclass
class InitStatus:
    """Status returned by endorlabs.init() after context bootstrap.

    Attributes:
        agent_knowledge_path: Materialized agent knowledge under context (sdk/).
        context_json_path: Path to context.json init manifest.
        platform_openapi_path: Path to downloaded OpenAPI spec (None if skipped).
        openapi_path: Alias for platform_openapi_path (REMOVE_BY_0_7_0).
        synced_skill_paths: Runtime skill mirrors refreshed during bootstrap.
        downloaded_at: Timestamp when bootstrap completed.

    """

    agent_knowledge_path: Path | None
    context_json_path: Path | None
    platform_openapi_path: Path | None
    downloaded_at: datetime
    synced_skill_paths: dict[str, Path] = field(default_factory=dict)

    @property
    def openapi_path(self) -> Path | None:
        """Alias for :attr:`platform_openapi_path`.

        REMOVE_BY_0_7_0: drop this alias; callers should use platform_openapi_path.
        """
        return self.platform_openapi_path

    @property
    def agent_knowledge_index_path(self) -> Path | None:
        """Tier-0 INDEX.md inside the materialized agent knowledge package."""
        if self.agent_knowledge_path is None:
            return None
        return self.agent_knowledge_path / "INDEX.md"

    @override
    def __repr__(self) -> str:
        """Return string representation of InitStatus."""
        parts = [f"InitStatus(downloaded_at={self.downloaded_at.isoformat()!r}"]
        if self.agent_knowledge_path:
            parts.append(f"agent_knowledge_path={self.agent_knowledge_path!r}")
        if self.context_json_path:
            parts.append(f"context_json_path={self.context_json_path!r}")
        if self.platform_openapi_path:
            parts.append(f"platform_openapi_path={self.platform_openapi_path!r}")
        if self.synced_skill_paths:
            parts.append(f"synced_skill_paths={self.synced_skill_paths!r}")
        return ", ".join(parts) + ")"
