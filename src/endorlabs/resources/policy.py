"""Policy resource module for Endor Labs API.

This module provides comprehensive policy management capabilities including
listing, examining, creating, updating, and deleting policies.

API OPERATIONS SUPPORTED:
- GET: List policies, Get policy by UUID
- POST: Create new policies
- PATCH: Update existing policies
- DELETE: Delete policies

API FEATURES:
- Full CRUD operations supported
- Policy type filtering (SYSTEM_FINDING, USER_FINDING, ADMISSION, ML_FINDING, etc.)
- OPA/Rego rule support
- Template system integration
- Project selector and exception support
- Namespace propagation control
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, override

from pydantic import BaseModel, Field, field_validator

from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
    FlexibleEnum,
)
from ..operations import BaseResourceOperations
from ..types import ListParameters
from ..utils.logging_config import get_resource_logger

if TYPE_CHECKING:
    from ..api_client import APIClient

logger = get_resource_logger(__name__)


class PolicyType(FlexibleEnum):
    """Policy type enumeration."""

    UNSPECIFIED = "POLICY_TYPE_UNSPECIFIED"
    ADMISSION = "POLICY_TYPE_ADMISSION"
    EXCEPTION = "POLICY_TYPE_EXCEPTION"
    FINDING = "POLICY_TYPE_FINDING"
    FINDING_CFG = "POLICY_TYPE_FINDING_CFG"
    ML_FINDING = "POLICY_TYPE_ML_FINDING"
    NOTIFICATION = "POLICY_TYPE_NOTIFICATION"
    REMEDIATION = "POLICY_TYPE_REMEDIATION"
    SYSTEM_FINDING = "POLICY_TYPE_SYSTEM_FINDING"
    USER_FINDING = "POLICY_TYPE_USER_FINDING"


class ExceptionReason(FlexibleEnum):
    """Exception reason enumeration."""

    UNSPECIFIED = "EXCEPTION_REASON_UNSPECIFIED"
    FALSE_POSITIVE = "EXCEPTION_REASON_FALSE_POSITIVE"
    IN_TRIAGE = "EXCEPTION_REASON_IN_TRIAGE"
    OTHER = "EXCEPTION_REASON_OTHER"
    RESOLVED = "EXCEPTION_REASON_RESOLVED"
    RISK_ACCEPTED = "EXCEPTION_REASON_RISK_ACCEPTED"


class PolicyRule(BaseModel):
    """Policy rule configuration."""

    action: str = Field(..., description="Rule action (ALLOW, DENY, WARN)")
    condition: str = Field(..., description="Rule condition")
    effect: str = Field(..., description="Rule effect")
    priority: int = Field(..., description="Rule priority")
    description: str = Field(..., description="Rule description")


class PolicySpec(BaseSpec):
    """Policy specification extending BaseSpec."""

    policy_type: PolicyType | None = Field(None, description="Policy type")
    rule: str | None = Field(None, description="Policy rule in text format")
    project_selector: list[str] | None = Field(
        None, description="Project selector tags"
    )
    project_exceptions: list[str] | None = Field(
        None, description="Project exception tags"
    )
    resource_kinds: list[str] | None = Field(None, description="Resource kinds")
    disable: bool | None = Field(False, description="Whether policy is disabled")
    finding: dict[str, Any] | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Finding configuration"
    )
    finding_level: str | None = Field(None, description="Finding level")
    query_statements: list[str] | None = Field(None, description="Query statements")
    template_uuid: str | None = Field(None, description="Template UUID")
    template_version: str | None = Field(None, description="Template version")
    template_parameters: list[dict[str, Any]] | None = Field(
        None, description="Template parameters"
    )
    template_values: dict[str, Any] | None = Field(None, description="Template values")
    admission: dict[str, Any] | None = Field(
        None, description="Admission configuration"
    )
    group_by_fields: list[str] | None = Field(None, description="Group by fields")
    notification: dict[str, Any] | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Notification configuration"
    )
    # exception is now defined in BaseSpec as ExceptionConfig
    # Keeping this for backward compatibility but it will use BaseSpec.exception
    finding_categories: list[str] | None = Field(
        None, description="Finding categories for policy filtering"
    )

    @field_validator("rule")
    @classmethod
    def validate_rule(cls, v: str | None) -> str | None:
        """Validate Rego rule syntax (basic checks)."""
        if v and not v.strip():
            raise ValueError("rule cannot be empty or whitespace")
        if v and not v.strip().startswith("package "):
            logger.warning("Rego rule should start with 'package' declaration")
        return v.strip() if v else v

    @field_validator("project_selector")
    @classmethod
    def validate_project_selector(cls, v: list[str] | None) -> list[str] | None:
        """Validate project selector tags are not empty strings."""
        if v:
            return [tag.strip() for tag in v if tag.strip()]
        return v

    @field_validator("project_exceptions")
    @classmethod
    def validate_project_exceptions(cls, v: list[str] | None) -> list[str] | None:
        """Validate project exception tags are not empty strings."""
        if v:
            return [tag.strip() for tag in v if tag.strip()]
        return v


class PolicyMeta(BaseMeta):
    """Policy metadata extending BaseMeta."""

    # Policy-specific fields only (universal fields inherited from BaseMeta)
    pass

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """Validate policy tags are not empty strings."""
        if v:
            return [tag.strip() for tag in v if tag.strip()]
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate policy name is not empty or whitespace."""
        if not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate policy description is not empty or whitespace."""
        if not v.strip():
            raise ValueError("description cannot be empty or whitespace")
        return v.strip()


class PolicyMetaUpdate(BaseModel):
    """Metadata for updating a Policy (only mutable fields)."""

    name: str | None = Field(None, description="Updated policy name")
    description: str | None = Field(None, description="Updated description")
    tags: list[str] | None = Field(None, description="Updated tags")
    annotations: dict[str, Any] | None = Field(None, description="Updated annotations")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """Validate policy tags are not empty strings."""
        if v:
            return [tag.strip() for tag in v if tag.strip()]
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Validate policy name is not empty or whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip() if v else v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Validate policy description is not empty or whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("description cannot be empty or whitespace")
        return v.strip() if v else v


class Policy(BaseResource):
    """Policy resource model extending BaseResource.

    OPERATION SUPPORT:
    ==================
    ✅ GET: List policies, Get by UUID
    ✅ POST: Create new policies
    ✅ PATCH: Update existing policies
    ✅ DELETE: Delete policies

    FIELD MUTABILITY:
    =================
    IMMUTABLE FIELDS (read-only, system-managed):
    - uuid: Unique identifier
    - meta.create_time, meta.created_by: Creation metadata
    - meta.update_time, meta.updated_by: Auto-managed timestamps
    - spec.policy_type: Policy type (set at creation)
    - spec.template_uuid: Template reference (set at creation)
    - tenant_meta.namespace: Namespace assignment

    MUTABLE FIELDS (can be updated via PATCH):
    - meta.name: Policy name
    - meta.description: Policy description
    - meta.tags: Policy tags
    - spec.rule: OPA/Rego rule definition
    - spec.disable: Enable/disable flag
    - spec.project_selector: Projects to apply policy to
    - spec.project_exceptions: Projects to exclude from policy
    - spec.template_values: Template configuration values
    - propagate: Whether to propagate to child namespaces

    FEATURES:
    =========
    - OPA/Rego rule support for custom policy logic
    - Template system for reusable policy patterns
    - Project selector and exception support
    - Multiple policy types (SYSTEM_FINDING, USER_FINDING, ADMISSION, ML_FINDING, etc.)
    - Namespace propagation control
    """

    # Policy-specific fields (universal fields inherited from BaseResource)
    spec: PolicySpec | None = Field(None, description="Policy specification")  # type: ignore

    model_config: ClassVar[dict[str, str]] = {"extra": "ignore"}

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift in policy responses."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "policy_type",
                "rule",
                "project_selector",
                "project_exceptions",
                "resource_kinds",
                "disable",
                "finding",
                "finding_level",
                "query_statements",
                "template_uuid",
                "template_version",
                "template_parameters",
                "template_values",
                "admission",
                "group_by_fields",
                "notification",
                "exception",
                "finding_categories",
            }

            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )

        return v

    @override
    @classmethod
    def get_mutable_fields_cls(cls) -> list[str]:
        """Get list of mutable fields for Policy."""
        return [
            "meta.name",
            "meta.description",
            "meta.tags",
            "spec.rule",
            "spec.disable",
            "spec.project_selector",
            "spec.project_exceptions",
            "spec.template_values",
            "propagate",
        ]

    @override
    @classmethod
    def get_immutable_fields_cls(cls) -> list[str]:
        """Get list of immutable fields for Policy."""
        return [
            "uuid",
            "meta.create_time",
            "meta.created_by",
            "meta.update_time",
            "meta.updated_by",
            "spec.policy_type",
            "spec.template_uuid",
            "tenant_meta.namespace",
        ]


class CreatePolicyPayload(BaseModel):
    """Payload for creating a new policy."""

    meta: PolicyMeta = Field(..., description="Policy metadata")
    spec: PolicySpec = Field(..., description="Policy specification")
    propagate: bool | None = Field(True, description="Propagate to child namespaces")


def build_create_payload(**kwargs: Any) -> CreatePolicyPayload:
    """Build CreatePolicyPayload from kwargs (decoupled facade create)."""
    return CreatePolicyPayload(**kwargs)


class UpdatePolicyPayload(BaseModel):
    r"""Payload for updating an Endor Labs policy.

    MUTABLE FIELDS (can be updated via PATCH):
    - meta.name: Policy name
    - meta.description: Policy description
    - meta.tags: Policy tags
    - spec.rule: OPA/Rego rule definition
    - spec.disable: Enable/disable flag
    - spec.project_selector: Projects to apply policy to
    - spec.project_exceptions: Projects to exclude from policy
    - spec.template_values: Template configuration values
    - propagate: Whether to propagate to child namespaces

    IMMUTABLE FIELDS (read-only, managed by API):
    - uuid: Unique identifier
    - meta.create_time, meta.created_by: Creation metadata
    - meta.update_time, meta.updated_by: Auto-managed timestamps
    - spec.policy_type: Policy type (set at creation)
    - spec.template_uuid: Template reference (set at creation)
    - tenant_meta.namespace: Namespace assignment

    Example:
        >>> payload = UpdatePolicyPayload(
        ...     meta=PolicyMetaUpdate(
        ...         name="Updated Policy Name",
        ...         description="Updated description",
        ...         tags=["security", "updated"]
        ...     ),
        ...     spec=PolicySpec(
        ...         policy_type=PolicyType.ML_FINDING,
        ...         rule="package updated\n...",
        ...         resource_kinds=[],
        ...         disable=False
        ...     )
        ... )
        >>> policy = update_policy(
        ...     client, namespace, uuid, payload, "meta.name,meta.description,spec.rule"
        ... )

    """

    meta: PolicyMetaUpdate | None = Field(None, description="Updated policy metadata")
    spec: PolicySpec | None = Field(None, description="Updated policy specification")
    propagate: bool | None = Field(None, description="Propagate to child namespaces")


# Convenience functions for common filtering patterns
def list_policies_by_type(
    client: APIClient, tenant_meta_namespace: str, policy_type: PolicyType
) -> list[Policy]:
    """List policies filtered by type."""
    list_params = ListParameters(  # pyright: ignore[reportCallIssue]
        filter=f"spec.policy_type=={policy_type.value}",
    )
    ops = BaseResourceOperations(client, "policies", Policy)
    return ops.list(tenant_meta_namespace, list_params)


def list_policies_by_namespace(
    client: APIClient, tenant_meta_namespace: str, target_namespace: str
) -> list[Policy]:
    """List policies filtered by namespace."""
    list_params = ListParameters(  # pyright: ignore[reportCallIssue]
        filter=f"tenant_meta.namespace=={target_namespace}",
    )
    ops = BaseResourceOperations(client, "policies", Policy)
    return ops.list(tenant_meta_namespace, list_params)


def list_policies_paginated(
    client: APIClient,
    tenant_meta_namespace: str,
    page_size: int = 10,
    page_token: str | None = None,
) -> list[Policy]:
    """List policies with pagination."""
    list_params = ListParameters(  # pyright: ignore[reportCallIssue]
        page_size=page_size,
        page_token=page_token,
    )
    ops = BaseResourceOperations(client, "policies", Policy)
    return ops.list(tenant_meta_namespace, list_params)


def list_policies_sorted(
    client: APIClient,
    tenant_meta_namespace: str,
    sort_by: str = "meta.create_time",
    desc: bool = True,
) -> list[Policy]:
    """List policies with sorting."""
    list_params = ListParameters(  # pyright: ignore[reportCallIssue]
        sort_by=sort_by,
        desc=desc,
    )
    ops = BaseResourceOperations(client, "policies", Policy)
    return ops.list(tenant_meta_namespace, list_params)
