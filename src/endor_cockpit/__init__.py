"""
Endor Cockpit SDK.

A Python SDK for the Endor Labs platform.
"""

from .api_client import APIClient
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
    user,
)

__version__ = "0.1.0"

__all__ = [
    "APIClient",
    "dependency_metadata",
    "finding",
    "installation",
    "linter_result",
    "metric",
    "namespace",
    "package_version",
    "policy",
    "project",
    "repository",
    "repository_version",
    "user",
]
