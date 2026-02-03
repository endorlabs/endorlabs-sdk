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

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar, override

from pydantic import BaseModel, Field, field_validator

from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseResourceOperations,
    BaseSpec,
    FlexibleEnum,
)
from ..types import ListParameters

if TYPE_CHECKING:
    from ..api_client import APIClient

logger = logging.getLogger(__name__)


def _get_policy_ops(client: APIClient) -> BaseResourceOperations[Policy]:
    """Get BaseResourceOperations instance for policies."""
    return BaseResourceOperations(client, "policies", Policy)


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


def list_policies(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[Policy]:
    """List all policies in a namespace with filtering support.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        list_params: Optional list parameters for filtering, masking, pagination
        max_pages: Optional maximum number of pages to fetch
        **kwargs: Additional query parameters (e.g. policy_type for legacy filter)

    Returns:
        List of Policy objects

    """
    ops = _get_policy_ops(client)
    policy_type = kwargs.pop("policy_type", None)

    # Handle legacy policy_type parameter
    if policy_type and list_params is None:
        list_params = ListParameters(  # pyright: ignore[reportCallIssue]
            filter=f"spec.policy_type=={policy_type.value}",
        )
    elif policy_type and list_params:
        type_filter = f"spec.policy_type=={policy_type.value}"
        list_params.filter = (
            f"({list_params.filter}) and ({type_filter})"
            if list_params.filter
            else type_filter
        )

    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def list_policies_iter(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[Policy]:
    """Iterate over policies without materializing the full list."""
    ops = _get_policy_ops(client)
    policy_type = kwargs.pop("policy_type", None)
    if policy_type and list_params is None:
        list_params = ListParameters(  # pyright: ignore[reportCallIssue]
            filter=f"spec.policy_type=={policy_type.value}",
        )
    elif policy_type and list_params:
        type_filter = f"spec.policy_type=={policy_type.value}"
        list_params.filter = (
            f"({list_params.filter}) and ({type_filter})"
            if list_params.filter
            else type_filter
        )
    return ops.list_iter(tenant_meta_namespace, list_params, max_pages, **kwargs)


def get_policy(
    client: APIClient, tenant_meta_namespace: str, policy_uuid: str
) -> Policy:
    """Get a specific policy by UUID with robust retrieval.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        policy_uuid: Policy UUID

    Returns:
        Policy object

    Raises:
        NotFoundError: If policy doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    ops = _get_policy_ops(client)
    return ops.get(tenant_meta_namespace, policy_uuid)


def create_policy(
    client: APIClient, tenant_meta_namespace: str, payload: CreatePolicyPayload
) -> Policy:
    """Create a new policy in a namespace with pre-validation and typed errors.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        payload: Policy creation payload

    Returns:
        Created Policy object

    Raises:
        ValidationError: If payload is invalid
        NotFoundError: If namespace doesn't exist
        PermissionDeniedError: If user lacks permission
        ConflictError: If policy already exists
        ServerError: If server error occurs

    """
    # Exclude immutable fields from meta (kind is set by API)
    # Create transformed payload for BaseResourceOperations
    meta_dict = payload.meta.model_dump(exclude={"kind"})
    # Ensure propagate is explicitly set (defaults to True if not provided)
    propagate_value = payload.propagate if payload.propagate is not None else True
    transformed_payload = CreatePolicyPayload(
        meta=PolicyMeta(**meta_dict),
        spec=payload.spec,
        propagate=propagate_value,
    )

    ops = _get_policy_ops(client)
    return ops.create(tenant_meta_namespace, transformed_payload)


def update_policy(
    client: APIClient,
    tenant_meta_namespace: str,
    policy_uuid: str,
    payload: UpdatePolicyPayload,
    update_mask: str,
) -> Policy | None:
    r"""Update an existing policy using partial updates.

    This function supports updating only specific fields using the update_mask
    parameter, which enables efficient partial updates without overwriting
    unchanged fields.

    IMPORTANT: Only policies created in the current namespace can be updated.
    Policies inherited from parent namespaces are immutable and will return
    404 errors when attempting to update.

    MUTABLE FIELDS (for policies created in current namespace):
    - meta.name: Policy name
    - meta.description: Policy description
    - meta.tags: Policy tags
    - spec.rule: OPA/Rego rule definition
    - spec.disable: Enable/disable flag
    - spec.project_selector: Projects to apply policy to
    - spec.project_exceptions: Projects to exclude from policy
    - spec.template_values: Template configuration values
    - propagate: Whether to propagate to child namespaces

    FIELD MUTABILITY (per OpenAPI spec):
    =====================================
    IMMUTABLE FIELDS (readOnly: true in API spec):
    - uuid: Unique identifier (readOnly: true in UpdatePolicy request body)
    - meta.create_time, meta.update_time, meta.upsert_time: Timestamps
      (readOnly: true in v1Meta)
    - meta.kind, meta.version: Resource metadata (readOnly: true in v1Meta)
    - meta.created_by, meta.updated_by: Audit fields (readOnly: true in v1Meta)
    - meta.references, meta.index_data: System-managed fields (readOnly: true in v1Meta)
    - tenant_meta.namespace: Namespace assignment

    MUTABLE FIELDS (NOT readOnly in API spec):
    - meta.name, meta.description, meta.tags: Metadata
    - spec.*: All PolicySpec fields (no readOnly fields in v1PolicySpec,
      including policy_type and template_uuid)
    - propagate: Whether to propagate to child namespaces

    Note: Inherited policies from parent namespaces cannot be updated
    (business logic constraint).

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        policy_uuid: Policy UUID
        payload: Policy update payload
        update_mask: Comma-separated list of fields to update (required), e.g.
            "meta.name,spec.rule". Missing or empty raises ValidationError.

    Returns:
        Updated Policy object

    Raises:
        ValidationError: If payload is invalid or update_mask is missing/empty
        NotFoundError: If policy doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    Example:
        >>> # Update policy name and description
        >>> payload = UpdatePolicyPayload(
        ...     meta=PolicyMetaUpdate(
        ...         name="Updated Policy",
        ...         description="Updated description"
        ...     )
        ... )
        >>> policy = update_policy(
        ...     client, namespace, uuid, payload, "meta.name,meta.description"
        ... )

        >>> # Update Rego rule
        >>> payload = UpdatePolicyPayload(
        ...     spec=PolicySpec(
        ...         policy_type=PolicyType.ML_FINDING,
        ...         rule="package updated\n...",
        ...         resource_kinds=[],
        ...         disable=False
        ...     )
        ... )
        >>> policy = update_policy(client, namespace, uuid, payload, "spec.rule")

    """
    from ..exceptions import ValidationError as EndorValidationError

    if not (update_mask and update_mask.strip()):
        raise EndorValidationError(
            message=(
                "Policy update requires an update_mask (e.g. 'meta.name', 'spec.rule')."
            ),
            operation="update",
            namespace=tenant_meta_namespace,
            resource_uuid=policy_uuid,
        )
    # Get the current policy to include required fields
    # Note: Using list_policies as workaround for get_policy 404 issues
    policies = list_policies(client, tenant_meta_namespace)
    current_policy = next((p for p in policies if p.uuid == policy_uuid), None)
    if not current_policy:
        from ..exceptions import NotFoundError

        raise NotFoundError(
            message=f"Policy {policy_uuid} not found",
            operation="update",
            namespace=tenant_meta_namespace,
            resource_uuid=policy_uuid,
        )

    # Merge current policy with payload updates
    merged_meta = {
        "name": current_policy.meta.name,  # Required field
        **(payload.meta.model_dump(exclude_none=True) if payload.meta else {}),
    }
    merged_spec = {
        **(current_policy.spec.model_dump() if current_policy.spec else {}),
        **(payload.spec.model_dump(exclude_none=True) if payload.spec else {}),
    }

    # Build merged policy object for base class
    tenant_meta_dict = (
        current_policy.tenant_meta.model_dump()
        if current_policy.tenant_meta
        else {"namespace": tenant_meta_namespace}
    )
    merged_policy_dict = {
        "uuid": policy_uuid,
        "tenant_meta": tenant_meta_dict,
        "meta": merged_meta,
        "spec": merged_spec,
    }
    if hasattr(payload, "propagate") and payload.propagate is not None:
        merged_policy_dict["propagate"] = payload.propagate

    # Create Policy object from merged data
    merged_policy = Policy(**merged_policy_dict)

    # Convert update_mask from string to List[str] for base class
    update_mask_list = [
        field.strip() for field in update_mask.split(",") if field.strip()
    ]

    # Use base class update method
    ops = _get_policy_ops(client)
    logger.info(f"Updating policy {policy_uuid} with mask: {update_mask}")
    return ops.update(
        tenant_meta_namespace, policy_uuid, merged_policy, update_mask_list
    )


def delete_policy(
    client: APIClient, tenant_meta_namespace: str, policy_uuid: str
) -> bool:
    """Delete a policy.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        policy_uuid: Policy UUID

    Returns:
        True if deletion successful, False otherwise

    """
    try:
        res = client.delete(
            f"v1/namespaces/{tenant_meta_namespace}/policies/{policy_uuid}"
        )
        return res.status_code == 200

    except Exception as e:
        logger.error(f"Error deleting policy {policy_uuid}: {e}", exc_info=True)
        return False


# Convenience functions for common filtering patterns
def list_policies_by_type(
    client: APIClient, tenant_meta_namespace: str, policy_type: PolicyType
) -> list[Policy]:
    """List policies filtered by type."""
    list_params = ListParameters(  # pyright: ignore[reportCallIssue]
        filter=f"spec.policy_type=={policy_type.value}",
    )
    return list_policies(client, tenant_meta_namespace, list_params=list_params)


def list_policies_by_namespace(
    client: APIClient, tenant_meta_namespace: str, target_namespace: str
) -> list[Policy]:
    """List policies filtered by namespace."""
    list_params = ListParameters(  # pyright: ignore[reportCallIssue]
        filter=f"tenant_meta.namespace=={target_namespace}",
    )
    return list_policies(client, tenant_meta_namespace, list_params=list_params)


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
    return list_policies(client, tenant_meta_namespace, list_params=list_params)


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
    return list_policies(client, tenant_meta_namespace, list_params=list_params)
