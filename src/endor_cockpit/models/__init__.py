"""
Data models for Endor Labs resources.

This module provides Pydantic models for all Endor Labs resources,
following a consistent pattern for type safety and validation.
"""

from .base import BaseResource, BaseMeta, BaseSpec, TenantMeta
from .project import Project, ProjectMeta, ProjectSpec, CreateProjectPayload, UpdateProjectPayload
from .finding import Finding, FindingMeta, FindingSpec, CreateFindingPayload, UpdateFindingPayload
from .policy import Policy, PolicyMeta, PolicySpec, CreatePolicyPayload, UpdatePolicyPayload
from .namespace import Namespace, NamespaceMeta, NamespaceSpec, CreateNamespacePayload, UpdateNamespacePayload

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
