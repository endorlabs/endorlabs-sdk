"""Project context directory helpers."""

from __future__ import annotations

from pathlib import Path

from endorlabs.context.paths import GITIGNORE_ENTRY
from endorlabs.utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)

__all__ = ["GITIGNORE_ENTRY", "warn_agent_defer_gitignore_to_user"]


def warn_agent_defer_gitignore_to_user(project_context_dir: Path) -> None:
    """Log guidance for agents when writing under the project context directory."""
    logger.warning(
        "Writing project context under %s. Agents: ask the user to add '%s' "
        "to the project .gitignore before committing; do not modify "
        ".gitignore automatically.",
        project_context_dir.resolve(),
        GITIGNORE_ENTRY,
    )
