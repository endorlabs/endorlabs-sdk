"""Context bootstrap for Endor Labs agentic workflows.

By default ``init()`` materializes agent knowledge under ``sdk/``. Use explicit flags
to download the OpenAPI spec or mirror skills into IDE discovery directories.

Product user documentation uses the Docs MCP server
(``https://docs.endorlabs.com/mcp``) — see
https://docs.endorlabs.com/introduction/docs-mcp-server

Example::

    >>> import endorlabs
    >>> status = endorlabs.init()
    >>> print(status.agent_knowledge_path)
    .endorlabs-context/sdk

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from .models import InitStatus
from .paths import (
    DEFAULT_CONTEXT_DIR,
    default_context_dir,
    platform_openapi_path,
)

if TYPE_CHECKING:
    from endorlabs.api_client import APIClient


# Lazy load _sync to defer optional dependency check until actually used

_sync_module: Any = None


def _get_sync() -> Any:
    """Lazy load the _sync module."""
    global _sync_module

    if _sync_module is None:
        from . import _sync

        _sync_module = _sync

    return _sync_module


def init(
    output_dir: str | Path = DEFAULT_CONTEXT_DIR,
    include_openapi: bool = False,
    include_agent_knowledge: bool = True,
    force: bool = False,
    sync_skills: Literal["none", "cursor", "claude", "both"] = "none",
    client: APIClient | None = None,
) -> InitStatus:
    """Bootstrap Endor Labs context for agentic workflows.

    See endorlabs.context._sync.init for full documentation.

    """
    return _get_sync().init(
        output_dir=output_dir,
        include_openapi=include_openapi,
        include_agent_knowledge=include_agent_knowledge,
        force=force,
        sync_skills=sync_skills,
        client=client,
    )


def sync_openapi(
    output_path: str | Path | None = None,
    force: bool = False,
    client: APIClient | None = None,
) -> Path:
    """Download OpenAPI specification from Endor Labs API.

    See endorlabs.context._sync.sync_openapi for full documentation.

    """
    resolved = (
        Path(output_path)
        if output_path is not None
        else platform_openapi_path(default_context_dir())
    )

    return _get_sync().sync_openapi(
        output_path=resolved,
        force=force,
        client=client,
    )


def sync_agent_skills(
    *,
    repo_root: str | Path = ".",
    target: Literal["none", "cursor", "claude", "both"] = "none",
    source_dir: str | Path | None = None,
) -> dict[str, Path]:
    """Mirror ``endor-*`` skills into runtime dirs; preserve non-endor entries."""
    return _get_sync().sync_agent_skills(
        repo_root=repo_root,
        target=target,
        source_dir=source_dir,
    )


__all__ = [
    "InitStatus",
    "init",
    "sync_agent_skills",
    "sync_openapi",
]
