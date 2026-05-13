"""Pre-commit helper to refresh local context and runtime skill mirrors."""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import endorlabs

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTEXT_DIR = REPO_ROOT / ".endorlabs-context"
SKILLS_PREFIX = "skills-src/"
CONTEXT_PREFIX = "src/endorlabs/context/"

logger = logging.getLogger(__name__)


def _normalize_paths(paths: Sequence[str]) -> tuple[str, ...]:
    """Normalize hook file paths for prefix matching."""
    normalized: list[str] = []
    for raw_path in paths:
        cleaned = raw_path.strip().replace("\\", "/")
        if cleaned:
            normalized.append(cleaned)
    return tuple(normalized)


def _requires_skill_sync(paths: Sequence[str]) -> bool:
    """Return whether the staged changes should refresh skill mirrors."""
    return any(path.startswith(SKILLS_PREFIX) for path in paths)


def _requires_context_refresh(paths: Sequence[str]) -> bool:
    """Return whether the staged changes should refresh local context."""
    return any(path.startswith(CONTEXT_PREFIX) for path in paths)


def _configured_skill_sync_target() -> Literal["cursor", "claude", "both"] | None:
    """Return explicit sync target for runtime mirrors already configured here."""
    has_cursor = (REPO_ROOT / ".cursor").exists()
    has_claude = (REPO_ROOT / ".claude").exists()
    if has_cursor and has_claude:
        return "both"
    if has_cursor:
        return "cursor"
    if has_claude:
        return "claude"
    if not has_cursor and not has_claude:
        return None
    return None


def _has_openapi_auth() -> bool:
    """Return whether credentials are available for OpenAPI refresh."""
    token = os.getenv("ENDOR_TOKEN")
    key = os.getenv("ENDOR_API_CREDENTIALS_KEY")
    secret = os.getenv("ENDOR_API_CREDENTIALS_SECRET")
    return bool(token or (key and secret))


def main(argv: Sequence[str] | None = None) -> int:
    """Refresh local generated context artifacts for maintainers."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    changed_paths = _normalize_paths(sys.argv[1:] if argv is None else argv)
    if not changed_paths:
        logger.info("No staged context or skill paths were provided.")
        return 0

    try:
        if _requires_skill_sync(changed_paths):
            sync_target = _configured_skill_sync_target()
            if sync_target is None:
                logger.info("Skill sync skipped; no runtime host mirror is configured.")
            else:
                synced_paths = endorlabs.sync_agent_skills(
                    repo_root=REPO_ROOT,
                    target=sync_target,
                )
                logger.info(
                    "Refreshed runtime skill mirrors: %s",
                    ", ".join(sorted(synced_paths)),
                )

        if _requires_context_refresh(changed_paths):
            if not CONTEXT_DIR.exists():
                logger.info(
                    "Skipping context refresh because %s does not exist.",
                    CONTEXT_DIR,
                )
                return 0
            include_openapi = _has_openapi_auth()
            status = endorlabs.init(
                output_dir=CONTEXT_DIR,
                include_openapi=include_openapi,
                include_user_docs=True,
                force=True,
                sync_skills="none",
            )
            logger.info(
                "Refreshed local context at %s (%d docs%s).",
                status.user_docs_path or CONTEXT_DIR,
                status.user_docs_count,
                " + OpenAPI" if status.openapi_path is not None else "",
            )
        return 0
    except Exception as exc:
        logger.error("Failed to refresh local context or skills: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
