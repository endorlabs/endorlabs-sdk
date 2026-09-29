"""Core sync logic for context bootstrap.

Downloads OpenAPI for local contract work and materializes agent knowledge.
Product user documentation is served via the Docs MCP server (not scraped).
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    from endorlabs.api_client import APIClient

from endorlabs.utils.logging_config import get_resource_logger

from ._project_context import warn_agent_defer_gitignore_to_user
from .models import InitStatus
from .paths import (
    DEFAULT_CONTEXT_DIR,
    context_json_path,
    platform_openapi_path,
    sdk_dir,
)

logger = get_resource_logger(__name__)

OPENAPI_PATH = "/download/openapiv2.swagger.json"
SKILLS_TARGETS: tuple[str, ...] = ("cursor",)
MANAGED_SKILL_PREFIX = "endor-"
SkillSyncMode = Literal["none", "cursor"]
CONTEXT_JSON_SCHEMA_VERSION = 1


def _normalize_skill_sync_mode(target: str) -> SkillSyncMode:
    """Validate and normalize a skill sync mode string."""
    normalized = target.strip().lower()
    valid_targets = {"none", "cursor"}
    if normalized not in valid_targets:
        raise ValueError(
            f"Unsupported sync_skills value {target!r}. "
            "Expected one of: none, cursor. "
            "(Claude Code uses AGENTS.md — sync_skills=claude/both were removed.)"
        )
    return cast("SkillSyncMode", normalized)


def _skill_target_dir(repo_root: Path, target: str) -> Path | None:
    """Return the runtime skills directory for a target host, or None if unknown."""
    if target == "cursor":
        return repo_root / ".cursor" / "skills"
    return None


def _resolve_skill_sync_targets(
    *,
    target: SkillSyncMode,
) -> tuple[str, ...]:
    """Resolve a sync mode to concrete runtime target names."""
    if target == "none":
        return ()
    if target in SKILLS_TARGETS:
        return (target,)
    return ()


def _managed_skill_rel_path(rel_path: Path) -> bool:
    """Return True when *rel_path* is under an Endor-managed skill directory."""
    top = rel_path.parts[0] if rel_path.parts else ""
    return top.startswith(MANAGED_SKILL_PREFIX)


def _prune_stale_skill_files(
    *,
    target_dir: Path,
    expected_rel_paths: set[str],
) -> None:
    """Remove stale Endor-managed skill files no longer present in the source tree."""
    if not target_dir.exists():
        return
    base_resolved = target_dir.resolve()
    stale_files = [
        path
        for path in target_dir.rglob("*")
        if path.is_file()
        and _managed_skill_rel_path(path.relative_to(target_dir))
        and path.relative_to(target_dir).as_posix() not in expected_rel_paths
    ]
    for path in stale_files:
        resolved = path.resolve()
        if not resolved.is_relative_to(base_resolved):
            continue
        resolved.unlink()
        parent = resolved.parent
        while parent != base_resolved and parent.exists():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


def _mirror_skill_tree(source_dir: Path, target_dir: Path) -> int:
    """Mirror Endor-managed (``endor-*``) skills into a runtime directory."""
    if not source_dir.exists():
        raise FileNotFoundError(f"Skills source directory does not exist: {source_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)
    base_resolved = target_dir.resolve()
    expected_rel_paths: set[str] = set()
    mirrored_files = 0

    for skill_dir in sorted(source_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        if not skill_dir.name.startswith(MANAGED_SKILL_PREFIX):
            logger.debug(
                "Skipping non-managed skill directory during mirror: %s",
                skill_dir.name,
            )
            continue
        for source_path in skill_dir.rglob("*"):
            if not source_path.is_file():
                continue
            rel_path = source_path.relative_to(source_dir)
            expected_rel_paths.add(rel_path.as_posix())
            dest_path = target_dir / rel_path
            resolved_dest = dest_path.resolve()
            if not resolved_dest.is_relative_to(base_resolved):
                raise ValueError(
                    "Skill mirror target "
                    f"{resolved_dest} escapes base directory {base_resolved}"
                )
            resolved_dest.parent.mkdir(parents=True, exist_ok=True)
            _ = shutil.copy2(source_path, resolved_dest)
            mirrored_files += 1

    _prune_stale_skill_files(
        target_dir=target_dir,
        expected_rel_paths=expected_rel_paths,
    )
    return mirrored_files


def sync_agent_skills(
    *,
    repo_root: str | Path = ".",
    target: SkillSyncMode = "none",
    source_dir: str | Path | None = None,
) -> dict[str, Path]:
    """Sync agent knowledge into runtime discovery paths.

    - cursor: mirrors endor-* skills to .cursor/skills/

    Claude Code reads repo-root ``AGENTS.md``; there is no CLAUDE.md generator.
    """
    repo_root_path = Path(repo_root)
    normalized_target = _normalize_skill_sync_mode(target)
    resolved_targets = _resolve_skill_sync_targets(
        target=normalized_target,
    )
    if not resolved_targets:
        logger.info(
            "Skill sync skipped for target=%s (no runtime target resolved).", target
        )
        return {}

    source_root = (
        Path(source_dir)
        if source_dir is not None
        else _resolve_skill_source_root(repo_root_path)
    )
    if not source_root.is_absolute():
        source_root = repo_root_path / source_root

    synced_paths: dict[str, Path] = {}
    for resolved_target in resolved_targets:
        if resolved_target == "cursor":
            target_dir = _skill_target_dir(repo_root_path, resolved_target)
            assert target_dir is not None
            mirrored_files = _mirror_skill_tree(source_root, target_dir)
            logger.info(
                "Synced %d skill files to %s runtime path %s",
                mirrored_files,
                resolved_target,
                target_dir,
            )
            synced_paths[resolved_target] = target_dir

    return synced_paths


def _resolve_skill_source_root(repo_root_path: Path) -> Path:
    """Resolve skill mirror source from materialized sdk/skills or wheel bundle."""
    materialized = sdk_dir(repo_root_path / DEFAULT_CONTEXT_DIR) / "skills"
    if materialized.is_dir():
        return materialized
    from endorlabs.agent_knowledge import agent_knowledge_dir

    return agent_knowledge_dir() / "skills"


def materialize_agent_knowledge(
    output_dir: str | Path,
    *,
    force: bool = False,
) -> Path:
    """Copy the wheel-shipped agent knowledge package into context sdk/."""
    from endorlabs.agent_knowledge import agent_knowledge_dir

    output_path = Path(output_dir)
    dest = sdk_dir(output_path)
    source = agent_knowledge_dir()
    if dest.exists() and not force:
        logger.info(
            "Agent knowledge already materialized: %s (use force=True to refresh)",
            dest,
        )
        return dest
    if dest.exists():
        shutil.rmtree(dest)
    _ = shutil.copytree(source, dest)
    from endorlabs.agent_knowledge import validate_agent_knowledge_tree

    validate_agent_knowledge_tree(dest)
    logger.info("Materialized agent knowledge to %s", dest)
    return dest


def write_context_json(
    *,
    output_dir: Path,
    sdk_version: str,
    agent_knowledge_path: Path | None,
    platform_openapi: Path | None,
    include_openapi: bool,
    sync_skills: SkillSyncMode,
) -> Path:
    """Write or update context.json init manifest."""
    manifest_path = context_json_path(output_dir)
    payload = {
        "schema_version": CONTEXT_JSON_SCHEMA_VERSION,
        "sdk_version": sdk_version,
        "materialized_at": datetime.now(UTC).isoformat(),
        "agent_knowledge_path": (
            str(agent_knowledge_path) if agent_knowledge_path else None
        ),
        "context_json_path": str(manifest_path),
        "platform_openapi_path": str(platform_openapi) if platform_openapi else None,
        "flags": {
            "include_openapi": include_openapi,
            "sync_skills": sync_skills,
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        _ = handle.write("\n")
    return manifest_path


def sync_openapi(
    output_path: str | Path | None = None,
    force: bool = False,
    client: APIClient | None = None,
) -> Path:
    """Download OpenAPI specification from Endor Labs API.

    Requires authentication via APIClient - no public URL fallback.

    Args:
        output_path: Path to save the OpenAPI spec file (default:
            ``.endorlabs/_cache/openapi.json``).
        force: Force re-download even if file exists.
        client: Optional APIClient instance. If not provided, one is created
            (requires ENDOR_API_CREDENTIALS_KEY/SECRET or ENDOR_TOKEN env vars).

    Returns:
        Path to the downloaded OpenAPI spec file.

    Raises:
        endorlabs.UnauthorizedError: If authentication fails.
        ImportError: If context dependencies are not installed.

    """
    from endorlabs.api_client import APIClient as APIClientClass

    output_file = (
        Path(output_path)
        if output_path is not None
        else platform_openapi_path(DEFAULT_CONTEXT_DIR)
    )

    # Skip if file exists and not forcing
    if output_file.exists() and not force:
        logger.info(
            "OpenAPI spec already exists: %s (use force=True to re-download)",
            output_path,
        )
        return output_file

    # Create client if not provided
    api_client = client or APIClientClass()

    logger.info("Downloading OpenAPI specification from Endor Labs API...")
    response = api_client.get(
        OPENAPI_PATH,
        headers={"Accept": "application/json"},
    )
    response_data = response.json()

    # Create directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(response_data, f, indent=2)

    logger.info("OpenAPI spec saved to: %s", output_path)
    return output_file


def init(
    output_dir: str | Path = DEFAULT_CONTEXT_DIR,
    include_openapi: bool = False,
    include_agent_knowledge: bool = True,
    force: bool = False,
    sync_skills: SkillSyncMode = "none",
    client: APIClient | None = None,
) -> InitStatus:
    """Bootstrap Endor Labs context for agentic workflows.

    By default, ``init()`` materializes agent knowledge under ``_cache/sdk/``. Pass
    explicit flags to download OpenAPI under ``_cache/`` and/or mirror skills into IDE
    discovery directories. Product docs use the Docs MCP server
    (``https://docs.endorlabs.com/mcp``), not a local scrape.

    Args:
        output_dir: Directory to save context files (default: .endorlabs).
        include_openapi: Download OpenAPI spec (default: False).
        include_agent_knowledge: Copy agent knowledge to _cache/sdk/ (default: True).
        force: Force re-download / refresh even if files exist (default: False).
        sync_skills: Mirror skills into runtime dirs
            (``none`` or ``cursor``; default ``none``). Claude Code uses
            repo-root ``AGENTS.md`` — there is no CLAUDE.md generator.
        client: Optional APIClient instance. If not provided, one is created
            when ``include_openapi=True`` (requires ENDOR_API_CREDENTIALS_KEY/
            SECRET or ENDOR_TOKEN env vars).

    Returns:
        InitStatus with paths to copied and downloaded files.

    Raises:
        endorlabs.UnauthorizedError: If OpenAPI authentication fails.

    Example::

        >>> import endorlabs
        >>> status = endorlabs.init()
        >>> print(status.agent_knowledge_path)
        .endorlabs/_cache/sdk

    """
    import importlib.metadata

    from endorlabs.api_client import APIClient as APIClientClass

    try:
        __version__ = importlib.metadata.version("endorlabs")
    except importlib.metadata.PackageNotFoundError:
        __version__ = "0.0.0.dev0"
    normalized_sync_target = _normalize_skill_sync_mode(sync_skills)
    needs_context_dir = (
        include_agent_knowledge or include_openapi or normalized_sync_target != "none"
    )
    if not needs_context_dir:
        logger.info(
            "No context bootstrap actions requested. Use agent_knowledge_index_path() "
            "for shipped skills without disk writes, or pass include_openapi=True, "
            "include_agent_knowledge=True, and/or sync_skills."
        )
        return InitStatus(
            agent_knowledge_path=None,
            context_json_path=None,
            platform_openapi_path=None,
            downloaded_at=datetime.now(UTC),
            synced_skill_paths={},
        )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    warn_agent_defer_gitignore_to_user(output_path)

    agent_knowledge_dest: Path | None = None
    if include_agent_knowledge:
        agent_knowledge_dest = materialize_agent_knowledge(output_path, force=force)

    platform_openapi: Path | None = None
    synced_skill_paths: dict[str, Path] = {}

    if include_openapi:
        api_client = client or APIClientClass()
        platform_openapi = sync_openapi(
            output_path=platform_openapi_path(output_path),
            force=force,
            client=api_client,
        )

    if normalized_sync_target != "none":
        skill_source = sdk_dir(output_path) / "skills"
        if not skill_source.is_dir():
            if include_agent_knowledge and agent_knowledge_dest is not None:
                skill_source = agent_knowledge_dest / "skills"
            else:
                from endorlabs.agent_knowledge import agent_knowledge_dir

                skill_source = agent_knowledge_dir() / "skills"
        synced_skill_paths = sync_agent_skills(
            repo_root=output_path.resolve().parent,
            target=normalized_sync_target,
            source_dir=skill_source,
        )

    manifest_path = write_context_json(
        output_dir=output_path,
        sdk_version=__version__,
        agent_knowledge_path=agent_knowledge_dest,
        platform_openapi=platform_openapi,
        include_openapi=include_openapi,
        sync_skills=normalized_sync_target,
    )

    return InitStatus(
        agent_knowledge_path=agent_knowledge_dest,
        context_json_path=manifest_path,
        platform_openapi_path=platform_openapi,
        downloaded_at=datetime.now(UTC),
        synced_skill_paths=synced_skill_paths,
    )
