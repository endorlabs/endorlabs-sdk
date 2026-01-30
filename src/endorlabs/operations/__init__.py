"""CRUD operations for Endor Labs resources.

This module provides high-level operations for all Endor Labs resources,
following a consistent pattern for API interaction.
"""

from ..resources.finding import (
    create_finding,
    delete_finding,
    get_finding,
    list_findings,
    update_finding,
)
from ..resources.namespace import (
    create_namespace,
    delete_namespace,
    get_namespace,
    list_namespaces,
    update_namespace,
)
from ..resources.policy import (
    create_policy,
    delete_policy,
    get_policy,
    list_policies,
    update_policy,
)
from ..resources.project import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)

__all__ = [
    "create_finding",
    "create_namespace",
    "create_policy",
    "create_project",
    "delete_finding",
    "delete_namespace",
    "delete_policy",
    "delete_project",
    "get_finding",
    "get_namespace",
    "get_policy",
    "get_project",
    # Finding operations
    "list_findings",
    # Namespace operations
    "list_namespaces",
    # Policy operations
    "list_policies",
    # Project operations
    "list_projects",
    "update_finding",
    "update_namespace",
    "update_policy",
    "update_project",
]
