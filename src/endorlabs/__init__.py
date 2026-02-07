"""Endor Labs SDK.

A Python SDK for the Endor Labs platform.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .api_client import APIClient
from .client_surface import Client
from .exceptions import (
    AmbiguousError,
    ConflictError,
    EndorAPIError,
    MethodNotSupportedError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
    UnauthorizedError,
    ValidationError,
    map_status_code_to_exception,
)
from .resources import (
    dependency_metadata,
    finding,
    installation,
    linter_result,
    metric,
    namespace,
    package_version,
    policy,
    project,
    repository,
    repository_version,
)

if TYPE_CHECKING:
    from .context.models import InitStatus

__version__ = "0.1.0"


def init(
    output_dir: str | Path = ".endorlabs-context",
    include_openapi: bool = True,
    include_user_docs: bool = True,
    max_pages: int | None = None,
    force: bool = False,
    client: APIClient | None = None,
) -> InitStatus:
    """Bootstrap Endor Labs context for agentic workflows.

    Downloads API specification and user documentation to a local directory.
    Requires authentication via APIClient - no public URL fallback.

    Args:
        output_dir: Directory to save context files (default: .endorlabs-context).
        include_openapi: Download OpenAPI spec (default: True).
        include_user_docs: Download user documentation (default: True).
        max_pages: Maximum number of user doc pages to download (default: all).
        force: Force re-download even if files exist (default: False).
        client: Optional APIClient instance. If not provided, one is created
            (requires ENDOR_API_CREDENTIALS_KEY/SECRET or ENDOR_TOKEN env vars).

    Returns:
        InitStatus with paths to downloaded files and metadata.

    Raises:
        UnauthorizedError: If authentication fails.
        ImportError: If context dependencies are not installed (for user docs).
            Install with: pip install endor-cockpit[context]

    Example::

        >>> import endorlabs
        >>> status = endorlabs.init()
        >>> print(status.openapi_path)
        .endorlabs-context/openapi.json

    """
    from .context import _sync

    return _sync.init(
        output_dir=output_dir,
        include_openapi=include_openapi,
        include_user_docs=include_user_docs,
        max_pages=max_pages,
        force=force,
        client=client,
    )


__all__ = [
    "APIClient",
    "AmbiguousError",
    "Client",
    "ConflictError",
    "EndorAPIError",
    "MethodNotSupportedError",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
    "ServerError",
    "UnauthorizedError",
    "ValidationError",
    "dependency_metadata",
    "finding",
    "init",
    "installation",
    "linter_result",
    "map_status_code_to_exception",
    "metric",
    "namespace",
    "package_version",
    "policy",
    "project",
    "repository",
    "repository_version",
]
