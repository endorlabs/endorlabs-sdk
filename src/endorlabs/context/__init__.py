"""Context bootstrap for Endor Labs agentic workflows.

By default ``init()`` materializes agent knowledge under ``sdk/``. Use explicit flags
to download platform context (OpenAPI spec and user documentation) or mirror skills
into IDE discovery directories.

Optional dependencies for user-docs sync::

    pip install endorlabs[docs]

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
    platform_user_docs_path,
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
    include_user_docs: bool = False,
    include_agent_knowledge: bool = True,
    max_pages: int | None = None,
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
        include_user_docs=include_user_docs,
        include_agent_knowledge=include_agent_knowledge,
        max_pages=max_pages,
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


def sync_user_docs(
    output_dir: str | Path | None = None,
    max_pages: int | None = None,
    timeout: int = 10,
    force: bool = False,
    max_concurrent: int | None = None,
) -> int:
    """Download user documentation pages and convert to markdown.

    See endorlabs.context._sync.sync_user_docs for full documentation.

    """
    resolved = (
        Path(output_dir)
        if output_dir is not None
        else platform_user_docs_path(default_context_dir())
    )

    return _get_sync().sync_user_docs(
        output_dir=resolved,
        max_pages=max_pages,
        timeout=timeout,
        force=force,
        max_concurrent=max_concurrent,
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
    "sync_user_docs",
]
