"""
Policy resource module for Endor Labs API.

This module provides comprehensive policy management capabilities including
listing, examining, creating, updating, and deleting policies.
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from ..api_client import APIClient

logger = logging.getLogger(__name__)


class PolicyType(str, Enum):
    """Policy type enumeration."""

    SYSTEM_FINDING = "POLICY_TYPE_SYSTEM_FINDING"
    USER_FINDING = "POLICY_TYPE_USER_FINDING"
    ADMISSION = "POLICY_TYPE_ADMISSION"
    ML_FINDING = "POLICY_TYPE_ML_FINDING"
    NOTIFICATION = "POLICY_TYPE_NOTIFICATION"


class PolicyRule(BaseModel):
    """Policy rule configuration."""

    action: str = Field(..., description="Rule action (ALLOW, DENY, WARN)")
    condition: str = Field(..., description="Rule condition")
    effect: str = Field(..., description="Rule effect")
    priority: int = Field(..., description="Rule priority")
    description: str = Field(..., description="Rule description")


class PolicySpec(BaseModel):
    """Policy specification."""

    policy_type: PolicyType = Field(..., description="Policy type")
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


class PolicyMeta(BaseModel):
    """Policy metadata."""

    name: str = Field(..., description="Policy name")
    description: str = Field(..., description="Policy description")
    kind: str = Field(default="Policy", description="Resource kind")
    tags: Optional[List[str]] = Field(default=None, description="Policy tags")
    create_time: Optional[str] = Field(default=None, description="Creation timestamp")
    update_time: Optional[str] = Field(default=None, description="Update timestamp")
    created_by: Optional[str] = Field(default=None, description="Created by")
    updated_by: Optional[str] = Field(default=None, description="Updated by")
    version: Optional[str] = Field(default="v1", description="Policy version")
    index_data: Optional[Dict[str, Any]] = Field(default=None, description="Index data")
    annotations: Optional[Dict[str, str]] = Field(
        default=None, description="Annotations"
    )
    parent_uuid: Optional[str] = Field(default=None, description="Parent UUID")
    parent_kind: Optional[str] = Field(default=None, description="Parent kind")
    upsert_time: Optional[str] = Field(default=None, description="Upsert timestamp")
    references: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = Field(
        default=None, description="References"
    )

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


class TenantMeta(BaseModel):
    """Tenant metadata."""

    namespace: str = Field(..., description="Tenant namespace")


class Policy(BaseModel):
    """Policy resource model."""

    uuid: str = Field(..., description="Policy UUID")
    tenant_meta: TenantMeta = Field(..., description="Tenant metadata")
    meta: PolicyMeta = Field(..., description="Policy metadata")
    spec: PolicySpec = Field(..., description="Policy specification")
    propagate: Optional[bool] = Field(True, description="Propagate to child namespaces")

    @field_validator("*", mode="before")
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift in policy responses."""
        if info.field_name in ["meta", "spec", "tenant_meta"] and isinstance(v, dict):
            # Log unknown fields for schema drift detection
            known_fields = {
                "meta": {
                    "name",
                    "description",
                    "kind",
                    "tags",
                    "create_time",
                    "update_time",
                    "created_by",
                    "updated_by",
                    "version",
                    "index_data",
                    "annotations",
                    "parent_uuid",
                    "parent_kind",
                    "upsert_time",
                    "references",
                },
                "spec": {
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
                },
                "tenant_meta": {"namespace"},
            }

            if info.field_name in known_fields:
                unknown_fields = set(v.keys()) - known_fields[info.field_name]
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
) -> List[Policy]:
    """
    List all policies in a namespace.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        policy_type: Optional policy type filter

    Returns:
        List of Policy objects
    """
    try:
        headers = client.default_headers
        res = client.get(
            f"v1/namespaces/{tenant_meta_namespace}/policies", headers=headers
        )
        data = res.json()

        # Parse response structure: {"list": {"objects": [...]}}
        objects = data.get("list", {}).get("objects", [])

        policies = []
        for obj in objects:
            try:
                policy = Policy(**obj)
                # Apply policy type filter if specified
                if policy_type is None or policy.spec.policy_type == policy_type:
                    policies.append(policy)
            except Exception as e:
                logger.warning(f"Failed to parse policy object: {e}")
                continue

        return policies

    except Exception as e:
        logger.error(f"Error listing policies: {e}", exc_info=True)
        return []


def get_policy(
    client: APIClient, tenant_meta_namespace: str, policy_uuid: str
) -> Optional[Policy]:
    """
    Get a specific policy by UUID.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        policy_uuid: Policy UUID

    Returns:
        Policy object or None if not found
    """
    try:
        headers = client.default_headers
        res = client.get(
            f"v1/namespaces/{tenant_meta_namespace}/policies/{policy_uuid}",
            headers=headers,
        )
        data = res.json()
        return Policy(**data)

    except Exception as e:
        logger.error(f"Error getting policy {policy_uuid}: {e}", exc_info=True)
        return None


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
        headers = client.default_headers
        headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

        request_data = {
            "meta": payload.meta.model_dump(),
            "spec": payload.spec.model_dump(),
            "propagate": payload.propagate,
        }

        res = client.post(
            f"v1/namespaces/{tenant_meta_namespace}/policies",
            headers=headers,
            data=request_data,
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

    IMMUTABLE FIELDS (cannot be updated):
    - uuid: Unique identifier
    - meta.create_time, meta.created_by: Creation metadata
    - meta.update_time, meta.updated_by: Auto-managed timestamps
    - spec.policy_type: Policy type (set at creation)
    - spec.template_uuid: Template reference (set at creation)
    - tenant_meta.namespace: Namespace assignment
    - Inherited policies from parent namespaces

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
        headers = client.default_headers
        headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

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
                        if payload.meta else {}
                    ),
                },
                "spec": {
                    **current_policy.spec.model_dump(),  # Include all
                    # existing spec fields
                    **(
                        payload.spec.model_dump(exclude_none=True)
                        if payload.spec else {}
                    ),
                },
            }
        }

        if update_mask:
            request_data["request"] = {"update_mask": update_mask}

        logger.info(f"Updating policy {policy_uuid} with mask: {update_mask}")

        res = client.patch(
            f"v1/namespaces/{tenant_meta_namespace}/policies",
            headers=headers,
            data=request_data,
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
        headers = client.default_headers
        res = client.delete(
            f"v1/namespaces/{tenant_meta_namespace}/policies/{policy_uuid}",
            headers=headers,
        )
        return res.status_code == 200

    except Exception as e:
        logger.error(f"Error deleting policy {policy_uuid}: {e}", exc_info=True)
        return False
