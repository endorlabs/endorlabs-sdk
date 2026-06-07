"""Project context directory helpers."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

GITIGNORE_ENTRY = ".endorlabs-context/"


def warn_agent_defer_gitignore_to_user(project_context_dir: Path) -> None:
    """Log guidance for agents when writing under the project context directory."""
    logger.warning(
        "Writing project context under %s. Agents: ask the user to add '%s' "
        "to the project .gitignore before committing; do not modify "
        ".gitignore automatically.",
        project_context_dir.resolve(),
        GITIGNORE_ENTRY,
    )
