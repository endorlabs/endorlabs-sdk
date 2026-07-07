"""Pre-commit helper to refresh local context and runtime skill mirrors."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import endorlabs
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.repo_paths import normalize_repo_paths

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTEXT_DIR = REPO_ROOT / ".endorlabs-context"
AGENT_PREFIX = "agent-knowledge/"
AGENT_KNOWLEDGE_SKILLS = REPO_ROOT / "src" / "endorlabs" / "agent_knowledge" / "skills"
AGENT_KNOWLEDGE_PREFIX = "src/endorlabs/agent_knowledge/"
CONTEXT_PREFIX = "src/endorlabs/context/"
SYNC_AGENT_KNOWLEDGE = REPO_ROOT / "devtools" / "sync_agent_knowledge.py"

logger = get_resource_logger(__name__)


def _requires_skill_sync(paths: Sequence[str]) -> bool:
    """Return whether the staged changes should refresh skill mirrors."""
    return any(
        path.startswith((AGENT_PREFIX, AGENT_KNOWLEDGE_PREFIX)) for path in paths
    )


def _requires_bundle_sync(paths: Sequence[str]) -> bool:
    """Return whether agent-knowledge/ changed and shipped package must regenerate."""
    return any(path.startswith(AGENT_PREFIX) for path in paths)


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
    return None


def _has_openapi_auth() -> bool:
    """Return whether credentials are available for OpenAPI refresh."""
    token = os.getenv("ENDOR_TOKEN")
    key = os.getenv("ENDOR_API_CREDENTIALS_KEY")
    secret = os.getenv("ENDOR_API_CREDENTIALS_SECRET")
    return bool(token or (key and secret))


def _run_bundle_sync() -> None:
    """Regenerate committed agent_knowledge artifacts from agent-knowledge/."""
    if not SYNC_AGENT_KNOWLEDGE.is_file():
        raise FileNotFoundError(f"Missing sync script: {SYNC_AGENT_KNOWLEDGE}")
    _ = subprocess.run(  # noqa: S603
        [sys.executable, str(SYNC_AGENT_KNOWLEDGE)],
        cwd=REPO_ROOT,
        check=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Refresh local generated context artifacts for maintainers."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    changed_paths = normalize_repo_paths(sys.argv[1:] if argv is None else argv)
    if not changed_paths:
        logger.info("No staged context or skill paths were provided.")
        return 0

    try:
        if _requires_bundle_sync(changed_paths):
            _run_bundle_sync()

        if _requires_skill_sync(changed_paths):
            sync_target = _configured_skill_sync_target()
            if sync_target is None:
                logger.info("Skill sync skipped; no runtime host mirror is configured.")
            else:
                if CONTEXT_DIR.exists() and (CONTEXT_DIR / "sdk" / "skills").is_dir():
                    source_dir = CONTEXT_DIR / "sdk" / "skills"
                    repo_root = REPO_ROOT
                else:
                    source_dir = AGENT_KNOWLEDGE_SKILLS
                    repo_root = REPO_ROOT
                synced_paths = endorlabs.sync_agent_skills(
                    repo_root=repo_root,
                    target=sync_target,
                    source_dir=source_dir,
                )
                logger.info(
                    "Refreshed runtime skill mirrors: %s",
                    ", ".join(f"{k}={v}" for k, v in sorted(synced_paths.items())),
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
                include_agent_knowledge=True,
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
