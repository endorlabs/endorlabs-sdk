"""
Policy resource module for Endor Labs API.

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

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from ..api_client import APIClient
from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseResourceOperations,
    BaseSpec,
    FlexibleEnum,
)
from ..types import ListParameters

logger = logging.getLogger(__name__)

# Global resource instance
_policy_ops = None


def _get_policy_ops(client: APIClient) -> BaseResourceOperations:
    """Get or create policy operations instance."""
    global _policy_ops
    if _policy_ops is None:
        _policy_ops = BaseResourceOperations(client, "policies", Policy)
    return _policy_ops


class PolicyType(FlexibleEnum):
    """Policy type enumeration."""

    SYSTEM_FINDING = "POLICY_TYPE_SYSTEM_FINDING"
    USER_FINDING = "POLICY_TYPE_USER_FINDING"
    ADMISSION = "POLICY_TYPE_ADMISSION"
    ML_FINDING = "POLICY_TYPE_ML_FINDING"
    NOTIFICATION = "POLICY_TYPE_NOTIFICATION"
    EXCEPTION = "POLICY_TYPE_EXCEPTION"


class ExceptionReason(FlexibleEnum):
    """Exception reason enumeration."""

    UNSPECIFIED = "EXCEPTION_REASON_UNSPECIFIED"
    FALSE_POSITIVE = "EXCEPTION_REASON_FALSE_POSITIVE"
    ACCEPTED_RISK = "EXCEPTION_REASON_ACCEPTED_RISK"
    MITIGATION = "EXCEPTION_REASON_MITIGATION"
    COMPLIANCE = "EXCEPTION_REASON_COMPLIANCE"
    BUSINESS_JUSTIFICATION = "EXCEPTION_REASON_BUSINESS_JUSTIFICATION"


class PolicyRule(BaseModel):
    """Policy rule configuration."""

    action: str = Field(..., description="Rule action (ALLOW, DENY, WARN)")
    condition: str = Field(..., description="Rule condition")
    effect: str = Field(..., description="Rule effect")
    priority: int = Field(..., description="Rule priority")
    description: str = Field(..., description="Rule description")


class PolicySpec(BaseSpec):
    """Policy specification extending BaseSpec."""

    policy_type: Optional[PolicyType] = Field(None, description="Policy type")
    rule: Optional[str] = Field(None, description="Policy rule in text format")
    project_selector: Optional[List[str]] = Field(
        None, description="Project selector tags"
    )
    project_exceptions: Optional[List[str]] = Field(
        None, description="Project exception tags"
    )
    resource_kinds: Optional[List[str]] = Field(None, description="Resource kinds")
    disable: Optional[bool] = Field(False, description="Whether policy is disabled")
    finding: Optional[Dict[str, Any]] = Field(None, description="Finding configuration")
    finding_level: Optional[str] = Field(None, description="Finding level")
    query_statements: Optional[List[str]] = Field(None, description="Query statements")
    template_uuid: Optional[str] = Field(None, description="Template UUID")
    template_version: Optional[str] = Field(None, description="Template version")
    template_parameters: Optional[List[Dict[str, Any]]] = Field(
        None, description="Template parameters"
    )
    template_values: Optional[Dict[str, Any]] = Field(
        None, description="Template values"
    )
    admission: Optional[Dict[str, Any]] = Field(
        None, description="Admission configuration"
    )
    group_by_fields: Optional[List[str]] = Field(None, description="Group by fields")
    notification: Optional[Dict[str, Any]] = Field(
        None, description="Notification configuration"
    )
    # exception is now defined in BaseSpec as ExceptionConfig
    # Keeping this for backward compatibility but it will use BaseSpec.exception
    finding_categories: Optional[List[str]] = Field(
        None, description="Finding categories for policy filtering"
    )

    @field_validator("rule")
    @classmethod
    def validate_rule(cls, v: Optional[str]) -> Optional[str]:
        """Validate Rego rule syntax (basic checks)."""
        if v and not v.strip():
            raise ValueError("rule cannot be empty or whitespace")
        if v and not v.strip().startswith("package "):
            logger.warning("Rego rule should start with 'package' declaration")
        return v.strip() if v else v

    @field_validator("project_selector")
    @classmethod
    def validate_project_selector(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate project selector tags are not empty strings."""
        if v:
            return [tag.strip() for tag in v if tag.strip()]
        return v

    @field_validator("project_exceptions")
    @classmethod
    def validate_project_exceptions(cls, v: Optional[List[str]]) -> Optional[List[str]]:
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
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
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


class Policy(BaseResource):
    """
    Policy resource model extending BaseResource.

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
    spec: Optional[PolicySpec] = Field(None, description="Policy specification")  # type: ignore

    model_config = {"extra": "ignore"}

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
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
    propagate: Optional[bool] = Field(True, description="Propagate to child namespaces")


class UpdatePolicyPayload(BaseModel):
    """
    Payload for updating an Endor Labs policy.

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
        ...     meta=PolicyMeta(
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

    meta: Optional[PolicyMeta] = Field(None, description="Updated policy metadata")
    spec: Optional[PolicySpec] = Field(None, description="Updated policy specification")
    propagate: Optional[bool] = Field(None, description="Propagate to child namespaces")


def list_policies(
    client: APIClient,
    tenant_meta_namespace: str,
    policy_type: Optional[PolicyType] = None,
    list_params: Optional[ListParameters] = None,
    **kwargs,
) -> List[Policy]:
    """
    List all policies in a namespace with filtering support.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        policy_type: Optional policy type filter (legacy parameter)
        list_params: Optional list parameters for filtering, masking, pagination
        **kwargs: Additional query parameters

    Returns:
        List of Policy objects
    """
    ops = _get_policy_ops(client)

    # Handle legacy policy_type parameter
    if policy_type and list_params is None:
        list_params = ListParameters(
            filter=f"spec.policy_type=={policy_type.value}",
            mask=None,
            page_size=None,
            page_token=None,
            sort_field=None,
            sort_order=None,
            count=None,
            include_child_namespaces=None,
            from_date=None,
            to_date=None,
        )
    elif policy_type and list_params:
        type_filter = f"spec.policy_type=={policy_type.value}"
        list_params.filter = (
            f"({list_params.filter}) and ({type_filter})"
            if list_params.filter
            else type_filter
        )

    return ops.list(tenant_meta_namespace, list_params, **kwargs)  # type: ignore


def get_policy(
    client: APIClient, tenant_meta_namespace: str, policy_uuid: str
) -> Optional[Policy]:
    """
    Get a specific policy by UUID with robust retrieval.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        policy_uuid: Policy UUID

    Returns:
        Policy object or None if not found
    """
    ops = _get_policy_ops(client)
    return ops.get(tenant_meta_namespace, policy_uuid)  # type: ignore


def create_policy(
    client: APIClient, tenant_meta_namespace: str, payload: CreatePolicyPayload
) -> Optional[Policy]:
    """
    Create a new policy in a namespace.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        payload: Policy creation payload

    Returns:
        Created Policy object or None if creation failed
    """
    try:
        request_data = {
            "meta": payload.meta.model_dump(),
            "spec": payload.spec.model_dump(),
            "propagate": payload.propagate,
        }

        res = client.post(
            f"v1/namespaces/{tenant_meta_namespace}/policies",
            json=request_data,
        )
        data = res.json()
        return Policy(**data)

    except Exception as e:
        logger.error(f"Error creating policy: {e}", exc_info=True)
        return None


def update_policy(
    client: APIClient,
    tenant_meta_namespace: str,
    policy_uuid: str,
    payload: UpdatePolicyPayload,
    update_mask: Optional[str] = None,
) -> Optional[Policy]:
    """
    Update an existing policy using partial updates.

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
        update_mask: Optional comma-separated list of fields to update
            (e.g., "meta.name,spec.rule"). If provided, only these
            fields will be updated. If omitted, all non-None fields in
            payload will be updated.

    Returns:
        Updated Policy object or None if update failed

    Raises:
        requests.exceptions.HTTPError: For API-level errors (403, 404, etc.)
        pydantic.ValidationError: If response data doesn't match expected schema

    Example:
        >>> # Update policy name and description
        >>> payload = UpdatePolicyPayload(
        ...     meta=PolicyMeta(
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

    Note:
        The update_mask parameter is critical for policy updates. Without it,
        the API may not persist changes reliably. Always specify which fields
        you want to update.
    """
    try:
        # Get the current policy to include required fields
        # Note: Using list_policies as workaround for get_policy 404 issues
        policies = list_policies(client, tenant_meta_namespace)
        current_policy = next((p for p in policies if p.uuid == policy_uuid), None)
        if not current_policy:
            logger.error(f"Policy {policy_uuid} not found")
            return None

        # Build request data with correct structure
        request_data = {
            "object": {
                "uuid": policy_uuid,
                "tenant_meta": current_policy.tenant_meta.model_dump(),
                "meta": {
                    "name": current_policy.meta.name,  # Required field
                    **(
                        payload.meta.model_dump(exclude_none=True)
                        if payload.meta
                        else {}
                    ),
                },
                "spec": {
                    **current_policy.spec.model_dump(),  # Include all
                    # existing spec fields
                    **(
                        payload.spec.model_dump(exclude_none=True)
                        if payload.spec
                        else {}
                    ),
                },
            }
        }

        if update_mask:
            request_data["request"] = {"update_mask": update_mask}

        logger.info(f"Updating policy {policy_uuid} with mask: {update_mask}")

        res = client.patch(
            f"v1/namespaces/{tenant_meta_namespace}/policies",
            json=request_data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        data = res.json()
        return Policy(**data)

    except Exception as e:
        logger.error(f"Error updating policy {policy_uuid}: {e}", exc_info=True)
        return None


def delete_policy(
    client: APIClient, tenant_meta_namespace: str, policy_uuid: str
) -> bool:
    """
    Delete a policy.

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
) -> List[Policy]:
    """List policies filtered by type."""
    list_params = ListParameters(
        filter=f"spec.policy_type=={policy_type.value}",
        mask=None,
        page_size=None,
        page_token=None,
        sort_field=None,
        sort_order=None,
        count=None,
        include_child_namespaces=None,
        from_date=None,
        to_date=None,
    )
    return list_policies(client, tenant_meta_namespace, list_params=list_params)


def list_policies_by_namespace(
    client: APIClient, tenant_meta_namespace: str, target_namespace: str
) -> List[Policy]:
    """List policies filtered by namespace."""
    list_params = ListParameters(
        filter=f"tenant_meta.namespace=={target_namespace}",
        mask=None,
        page_size=None,
        page_token=None,
        sort_field=None,
        sort_order=None,
        count=None,
        include_child_namespaces=None,
        from_date=None,
        to_date=None,
    )
    return list_policies(client, tenant_meta_namespace, list_params=list_params)


def list_policies_with_mask(
    client: APIClient, tenant_meta_namespace: str, fields: List[str]
) -> List[Policy]:
    """List policies with field masking."""
    list_params = ListParameters(
        filter=None,
        mask=",".join(fields),
        page_size=None,
        page_token=None,
        sort_field=None,
        sort_order=None,
        count=None,
        include_child_namespaces=None,
        from_date=None,
        to_date=None,
    )
    return list_policies(client, tenant_meta_namespace, list_params=list_params)


def list_policies_paginated(
    client: APIClient,
    tenant_meta_namespace: str,
    page_size: int = 10,
    page_token: Optional[str] = None,
) -> List[Policy]:
    """List policies with pagination."""
    list_params = ListParameters(
        filter=None,
        mask=None,
        page_size=page_size,
        page_token=page_token,
        sort_field=None,
        sort_order=None,
        count=None,
        include_child_namespaces=None,
        from_date=None,
        to_date=None,
    )
    return list_policies(client, tenant_meta_namespace, list_params=list_params)


def list_policies_sorted(
    client: APIClient,
    tenant_meta_namespace: str,
    sort_field: str = "meta.create_time",
    desc: bool = True,
) -> List[Policy]:
    """List policies with sorting."""
    list_params = ListParameters(
        filter=None,
        mask=None,
        page_size=None,
        page_token=None,
        sort_field=sort_field,
        sort_order="desc" if desc else "asc",
        count=None,
        include_child_namespaces=None,
        from_date=None,
        to_date=None,
    )
    return list_policies(client, tenant_meta_namespace, list_params=list_params)
