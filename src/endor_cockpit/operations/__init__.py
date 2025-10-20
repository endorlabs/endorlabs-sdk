"""
CRUD operations for Endor Labs resources.

This module provides high-level operations for all Endor Labs resources,
following a consistent pattern for API interaction.
"""

from .finding import (
    create_finding,
    delete_finding,
    get_finding,
    list_findings,
    update_finding,
)
from .namespace import (
    create_namespace,
    delete_namespace,
    get_namespace,
    list_namespaces,
    update_namespace,
)
from .policy import (
    create_policy,
    delete_policy,
    get_policy,
    list_policies,
    update_policy,
)
from .project import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)

__all__ = [
    # Project operations
    "list_projects",
    "get_project",
    "create_project",
    "update_project",
    "delete_project",

    # Finding operations
    "list_findings",
    "get_finding",
    "create_finding",
    "update_finding",
    "delete_finding",

    # Policy operations
    "list_policies",
    "get_policy",
    "create_policy",
    "update_policy",
    "delete_policy",

    # Namespace operations
    "list_namespaces",
    "get_namespace",
    "create_namespace",
    "update_namespace",
    "delete_namespace",
]
