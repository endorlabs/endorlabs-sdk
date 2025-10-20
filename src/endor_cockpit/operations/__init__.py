"""
CRUD operations for Endor Labs resources.

This module provides high-level operations for all Endor Labs resources,
following a consistent pattern for API interaction.
"""

from .project import (
    list_projects, get_project, create_project, update_project, delete_project
)
from .finding import (
    list_findings, get_finding, create_finding, update_finding, delete_finding
)
from .policy import (
    list_policies, get_policy, create_policy, update_policy, delete_policy
)
from .namespace import (
    list_namespaces, get_namespace, create_namespace, update_namespace, delete_namespace
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
