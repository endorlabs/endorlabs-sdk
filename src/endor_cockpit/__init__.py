"""Endor Cockpit SDK.

A Python SDK for the Endor Labs platform.
"""

from .api_client import APIClient
from .exceptions import (
    ConflictError,
    EndorAPIError,
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

__version__ = "0.1.0"

__all__ = [
    "APIClient",
    "ConflictError",
    "EndorAPIError",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
    "ServerError",
    "UnauthorizedError",
    "ValidationError",
    "dependency_metadata",
    "finding",
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
