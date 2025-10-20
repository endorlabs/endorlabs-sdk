"""
Data models for Endor Labs resources.

This module provides Pydantic models for all Endor Labs resources,
following a consistent pattern for type safety and validation.
"""

from .base import BaseMeta, BaseResource, BaseSpec, TenantMeta
from .finding import (
    CreateFindingPayload,
    Finding,
    FindingMeta,
    FindingSpec,
    UpdateFindingPayload,
)
from .namespace import (
    CreateNamespacePayload,
    Namespace,
    NamespaceMeta,
    NamespaceSpec,
    UpdateNamespacePayload,
)
from .policy import (
    CreatePolicyPayload,
    Policy,
    PolicyMeta,
    PolicySpec,
    UpdatePolicyPayload,
)
from .project import (
    CreateProjectPayload,
    Project,
    ProjectMeta,
    ProjectSpec,
    UpdateProjectPayload,
)

__all__ = [
    # Base classes
    "BaseResource",
    "BaseMeta",
    "BaseSpec",
    "TenantMeta",
    # Project models
    "Project",
    "ProjectMeta",
    "ProjectSpec",
    "CreateProjectPayload",
    "UpdateProjectPayload",
    # Finding models
    "Finding",
    "FindingMeta",
    "FindingSpec",
    "CreateFindingPayload",
    "UpdateFindingPayload",
    # Policy models
    "Policy",
    "PolicyMeta",
    "PolicySpec",
    "CreatePolicyPayload",
    "UpdatePolicyPayload",
    # Namespace models
    "Namespace",
    "NamespaceMeta",
    "NamespaceSpec",
    "CreateNamespacePayload",
    "UpdateNamespacePayload",
]
