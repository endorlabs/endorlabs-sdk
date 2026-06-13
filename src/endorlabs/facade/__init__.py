"""Resource facade package for the Client API.

Provides ``ResourceRuntimeFacade[T]`` and resource-specific facades.
See docs/reference/resources.md and docs/guides/retrieving-scan-results.md.
"""

from ..operations import BaseResourceOperations
from .base import ListableFacade
from .context_partition import context_partition_filter, main_context_filter
from .runtime import ResourceRuntimeFacade
from .specialized import (
    FACADE_CLASS_BY_ATTR,
    CallGraphDataFacade,
    FindingFacade,
    ProjectFacade,
    ScanResultFacade,
)

_ListableFacade = ListableFacade
ResourceFacade = ResourceRuntimeFacade

__all__ = [
    "FACADE_CLASS_BY_ATTR",
    "BaseResourceOperations",
    "CallGraphDataFacade",
    "FindingFacade",
    "ListableFacade",
    "ProjectFacade",
    "ResourceFacade",
    "ResourceRuntimeFacade",
    "ScanResultFacade",
    "_ListableFacade",
    "context_partition_filter",
    "main_context_filter",
]
