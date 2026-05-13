"""Context bootstrap for Endor Labs agentic workflows.

This module provides functionality to download Endor Labs context
(API specification and user documentation) for use with AI agents.

Requires authentication via APIClient and optional dependencies::

    pip install endorlabs-sdk[context]

Example::

    >>> import endorlabs
    >>> status = endorlabs.init()  # downloads to .endorlabs-context/
    >>> print(status.openapi_path)

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from .models import InitStatus

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
    output_dir: str | Path = ".endorlabs-context",
    include_openapi: bool = True,
    include_user_docs: bool = True,
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
        max_pages=max_pages,
        force=force,
        sync_skills=sync_skills,
        client=client,
    )


def sync_openapi(
    output_path: str | Path = ".endorlabs-context/openapiv2.swagger.json",
    force: bool = False,
    client: APIClient | None = None,
) -> Path:
    """Download OpenAPI specification from Endor Labs API.

    See endorlabs.context._sync.sync_openapi for full documentation.
    """
    return _get_sync().sync_openapi(
        output_path=output_path,
        force=force,
        client=client,
    )


def sync_user_docs(
    output_dir: str | Path = ".endorlabs-context/docs",
    max_pages: int | None = None,
    timeout: int = 10,
    force: bool = False,
    max_concurrent: int | None = None,
) -> int:
    """Download user documentation pages and convert to markdown.

    See endorlabs.context._sync.sync_user_docs for full documentation.
    """
    return _get_sync().sync_user_docs(
        output_dir=output_dir,
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
    """Mirror repo skill sources into runtime discovery directories."""
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
