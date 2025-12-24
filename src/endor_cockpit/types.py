"""
Type definitions for Endor Cockpit SDK.

This module provides common type definitions used across the SDK
for enhanced type safety and LLM understanding.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

# Resource Types
ResourceType = Literal[
    "Project",
    "Finding",
    "Policy",
    "Namespace",
    "Repository",
    "RepositoryVersion",
    "PackageVersion",
]

# Operation Types
OperationType = Literal["list", "get", "create", "update", "delete"]

# Status Types
StatusType = Literal["active", "inactive", "pending", "completed", "failed"]

# Severity Types
SeverityType = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]

# Platform Types
PlatformType = Literal[
    "PLATFORM_SOURCE_GITHUB",
    "PLATFORM_SOURCE_GITLAB",
    "PLATFORM_SOURCE_BITBUCKET",
    "PLATFORM_SOURCE_AZURE_DEVOPS",
]

# Ecosystem Types
EcosystemType = Literal[
    "ECOSYSTEM_NPM",
    "ECOSYSTEM_PYPI",
    "ECOSYSTEM_MAVEN",
    "ECOSYSTEM_NUGET",
    "ECOSYSTEM_RUBYGEMS",
    "ECOSYSTEM_GO",
    "ECOSYSTEM_RUST",
    "ECOSYSTEM_DOCKER",
]

# Finding Categories
FindingCategoryType = Literal[
    "FINDING_CATEGORY_VULNERABILITY",
    "FINDING_CATEGORY_SUPPLY_CHAIN",
    "FINDING_CATEGORY_LICENSE_RISK",
    "FINDING_CATEGORY_SECURITY",
    "FINDING_CATEGORY_SECRETS",
    "FINDING_CATEGORY_MALWARE",
]

# Policy Types
PolicyType = Literal[
    "POLICY_TYPE_SYSTEM_FINDING",
    "POLICY_TYPE_USER_FINDING",
    "POLICY_TYPE_ADMISSION",
    "POLICY_TYPE_ML_FINDING",
    "POLICY_TYPE_NOTIFICATION",
]


# TypedDict Definitions
class ResourceMeta(TypedDict, total=False):
    """Common metadata structure for all resources."""

    name: str
    description: Optional[str]
    create_time: Optional[str]
    created_by: Optional[str]
    update_time: Optional[str]
    updated_by: Optional[str]
    tags: Optional[List[str]]


class TenantMeta(TypedDict):
    """Tenant metadata structure."""

    namespace: str


class APIResponse(TypedDict, total=False):
    """Standard API response structure."""

    list: Dict[str, Any]
    objects: List[Dict[str, Any]]
    total: Optional[int]
    next_page_token: Optional[str]


class ErrorResponse(TypedDict):
    """Error response structure."""

    error: str
    message: str
    code: int
    details: Optional[Dict[str, Any]]


# Generic Types
ResourceDict = Dict[str, Any]
ResourceList = List[ResourceDict]
NamespaceStr = str
UUIDStr = str
TagList = List[str]
UpdateMask = str

# Function Signatures
ResourceOperation = Literal[
    "list_projects",
    "get_project",
    "create_project",
    "update_project",
    "delete_project",
    "list_findings",
    "get_finding",
    "create_finding",
    "update_finding",
    "delete_finding",
    "list_policies",
    "get_policy",
    "create_policy",
    "update_policy",
    "delete_policy",
    "list_namespaces",
    "get_namespace",
    "create_namespace",
    "update_namespace",
    "delete_namespace",
]

# Validation Types
ValidationResult = TypedDict(
    "ValidationResult", {"valid": bool, "errors": List[str], "warnings": List[str]}
)

# Schema Drift Types
SchemaDriftInfo = TypedDict(
    "SchemaDriftInfo",
    {"model_name": str, "unknown_fields": List[str], "context": str, "timestamp": str},
)


# Universal List Parameters
class ListParameters(BaseModel):
    """Universal list parameters for all Endor Labs resources."""

    filter: Optional[str] = Field(
        None,
        description="Filter expression (e.g., 'spec.level==FINDING_LEVEL_CRITICAL')",
    )
    mask: Optional[str] = Field(
        None, description="Field mask (e.g., 'meta.name,spec.level')"
    )
    page_size: Optional[int] = Field(None, description="Results per page")
    page_token: Optional[str] = Field(None, description="Page token for pagination")
    sort_field: Optional[str] = Field(
        None, description="Sort field (e.g., 'meta.create_time')"
    )
    sort_order: Optional[str] = Field("asc", description="Sort order (asc/desc)")
    count: Optional[bool] = Field(
        None, description="Count only (return count instead of objects)"
    )
    traverse: Optional[bool] = Field(
        None,
        description=(
            "Traverse all child namespaces recursively. "
            "When True, automatically queries all namespaces in the hierarchy. "
            "Recommended for tenant-wide queries (e.g., all dependencies across all namespaces)."
        ),
    )
    from_date: Optional[str] = Field(
        None, description="Created after date (ISO format)"
    )
    to_date: Optional[str] = Field(None, description="Created before date (ISO format)")
