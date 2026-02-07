"""Type definitions for Endor Cockpit SDK.

This module provides common type definitions used across the SDK
for enhanced type safety and LLM understanding.
"""
# APIResponse uses key "list" (API contract); Pyright treats it as builtin
# pyright: reportInvalidTypeForm=false

from typing import Any, Literal, Protocol

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


class SupportsResourceUpdate(Protocol):
    """Protocol for facade that can perform resource update.

    Used by BaseResource.update(facade, **kwargs) so resources do not
    depend on the concrete Client or ResourceFacade.
    """

    def update(
        self,
        id_or_resource: Any,
        payload: Any = None,
        *,
        update_mask: str,
        namespace: Any = None,
    ) -> Any:
        """Update by ID or resource; payload and update_mask required."""
        ...


# TypedDict Definitions
class ResourceMeta(TypedDict, total=False):
    """Common metadata structure for all resources."""

    name: str
    description: str | None
    create_time: str | None
    created_by: str | None
    update_time: str | None
    updated_by: str | None
    tags: list[str] | None


class TenantMeta(TypedDict):
    """Tenant metadata structure."""

    namespace: str


class APIResponse(TypedDict, total=False):
    """Standard API response structure (API returns key 'list')."""

    list: dict[str, Any]
    objects: list[dict[str, Any]]
    total: int | None
    next_page_token: str | None


class ErrorResponse(TypedDict):
    """Error response structure."""

    error: str
    message: str
    code: int
    details: dict[str, Any] | None


# Generic Types
ResourceDict = dict[str, Any]
ResourceList = list[ResourceDict]
NamespaceStr = str
UUIDStr = str
TagList = list[str]
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
class ValidationResult(TypedDict):
    """Result of validation with errors and warnings."""

    valid: bool
    errors: list[str]
    warnings: list[str]


# Schema Drift Types
class SchemaDriftInfo(TypedDict):
    """Schema drift detection result with unknown fields and context."""

    model_name: str
    unknown_fields: list[str]
    context: str
    timestamp: str


# Universal List Parameters
# Common list params are exposed as explicit facade kwargs; all params map to
# list_parameters.* on the wire. Names follow API spec in snake_case.
class ListParameters(BaseModel):
    """Universal list parameters for all Endor Labs resources."""

    filter: str | None = Field(
        None,
        description="Filter expression (e.g., 'spec.level==FINDING_LEVEL_CRITICAL')",
    )
    mask: str | None = Field(
        None, description="Field mask (e.g., 'meta.name,spec.level')"
    )
    page_size: int | None = Field(None, description="Results per page")
    page_token: str | None = Field(None, description="Page token for pagination")
    page_id: str | None = Field(
        None, description="Page id to start from (alternative pagination)"
    )
    sort_field: str | None = Field(
        None,
        description=(
            "Deprecated: use sort_by instead. "
            "Sort field (e.g., 'meta.create_time')"
        ),
    )
    sort_order: str | None = Field(
        "asc",
        description="Deprecated: use desc instead. Sort order (asc/desc)",
    )
    sort_by: str | None = Field(
        None,
        description="Field path to sort by (e.g., 'meta.create_time').",
    )
    desc: bool | None = Field(
        None,
        description="Sort descending when True, ascending when False or omitted.",
    )
    count: bool | None = Field(
        None, description="Count only (return count instead of objects)"
    )
    traverse: bool | None = Field(
        None,
        description=(
            "Traverse all child namespaces recursively. "
            "When True, automatically queries all namespaces in the hierarchy. "
            "Use for tenant-wide queries "
            "(e.g., all dependencies across all namespaces)."
        ),
    )
    from_date: str | None = Field(None, description="Created after date (ISO format)")
    to_date: str | None = Field(None, description="Created before date (ISO format)")
    archive: bool | None = Field(
        None,
        description="When True, fetch resources from the archive.",
    )
    list_all: bool | None = Field(
        True,
        description="List all resources (use with timeout for large result sets).",
    )
    pr_uuid: str | None = Field(
        None,
        description="Only list resources from this PR scan.",
    )
    # Grouping / aggregation (endorctl: group-aggregation-paths, group-by-time, etc.)
    group_aggregation_paths: list[str] | None = Field(
        None,
        description="Fields to group resources by.",
    )
    group_by_time: bool | None = Field(
        None,
        description="Group resources by time.",
    )
    group_by_time_field_value: str | None = Field(
        None,
        description="Message field used for time aggregation.",
    )
    group_by_time_interval: str | None = Field(
        None,
        description=(
            "Time interval: year, quarter, month, week, day, hour, minute, second."
        ),
    )
    group_by_time_mode: str | None = Field(
        None,
        description="Group-by-time output mode: count or sum.",
    )
    group_by_time_operator: str | None = Field(
        None,
        description="Aggregation operator: min, max, avg, sum.",
    )
    group_show_aggregation_uuids: bool | None = Field(
        None,
        description="Include resource UUIDs in each group.",
    )
    group_unique_count_paths: list[str] | None = Field(
        None,
        description="Count unique values for these fields in the group.",
    )
    group_unique_value_paths: list[str] | None = Field(
        None,
        description="Return unique values for these fields in the group.",
    )
