"""
Authorization Policy resource module for Endor Labs API.

This module provides comprehensive authorization policy management capabilities
including listing, examining, creating, updating, and deleting authorization policies.

API OPERATIONS SUPPORTED:
- GET: List authorization policies, Get authorization policy by UUID
- POST: Create new authorization policies
- PATCH: Update existing authorization policies
- DELETE: Delete authorization policies

API FEATURES:
- Full CRUD operations supported
- System role-based permissions (ADMIN, READ_ONLY, CODE_SCANNER, etc.)
- Resource-specific permission rules
- Authorization clause matching
- Namespace targeting and propagation
- Expiration time support
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
_authorization_policy_ops = None


def _get_authorization_policy_ops(
    client: APIClient,
) -> BaseResourceOperations:
    """Get or create authorization policy operations instance."""
    global _authorization_policy_ops
    if _authorization_policy_ops is None:
        _authorization_policy_ops = BaseResourceOperations(
            client, "authorization-policies", AuthorizationPolicy
        )
    return _authorization_policy_ops


class SystemRole(FlexibleEnum):
    """System role enumeration for authorization policies."""

    UNSPECIFIED = "SYSTEM_ROLE_UNSPECIFIED"
    ADMIN = "SYSTEM_ROLE_ADMIN"
    READ_ONLY = "SYSTEM_ROLE_READ_ONLY"
    POLICY_EDITOR = "SYSTEM_ROLE_POLICY_EDITOR"
    CODE_SCANNER = "SYSTEM_ROLE_CODE_SCANNER"
    ENDOR_PATCHING = "SYSTEM_ROLE_ENDOR_PATCHING"
    SYNC_ORG = "SYSTEM_ROLE_SYNC_ORG"
    ONPREM_SCHEDULER = "SYSTEM_ROLE_ONPREM_SCHEDULER"


class Method(FlexibleEnum):
    """Method enumeration for permission rules."""

    UNSPECIFIED = "METHOD_UNSPECIFIED"
    READ = "METHOD_READ"
    CREATE = "METHOD_CREATE"
    UPDATE = "METHOD_UPDATE"
    DELETE = "METHOD_DELETE"
    ALL = "METHOD_ALL"


class PermissionsMethods(BaseModel):
    """Methods configuration for resource permissions."""

    methods: List[str] = Field(
        ..., description="Array of allowed methods (e.g., ['METHOD_READ', 'METHOD_CREATE'])"
    )


class AuthorizationPolicyPermissions(BaseModel):
    """Permissions configuration for authorization policy."""

    roles: Optional[List[str]] = Field(
        None,
        description="System roles - predefined role-based permissions (e.g., SYSTEM_ROLE_READ_ONLY, SYSTEM_ROLE_ADMIN)",
    )
    rules: Optional[Dict[str, Dict[str, List[str]]]] = Field(
        None,
        description="Resource-specific permissions - maps resource types to allowed methods (e.g., {'repository': {'methods': ['METHOD_READ', 'METHOD_CREATE']}})",
    )
    except_resources: Optional[List[str]] = Field(
        None,
        description="Excluded resources - list of resources to exclude from wildcard permissions",
    )

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate roles are not empty strings."""
        if v:
            return [role.strip() for role in v if role.strip()]
        return v

    @field_validator("except_resources")
    @classmethod
    def validate_except_resources(
        cls, v: Optional[List[str]]
    ) -> Optional[List[str]]:
        """Validate except_resources are not empty strings."""
        if v:
            return [resource.strip() for resource in v if resource.strip()]
        return v


class AuthorizationPolicySpec(BaseSpec):
    """Authorization policy specification extending BaseSpec."""

    clause: List[str] = Field(
        ...,
        description="""Authorization clauses - list of claims that must match (AND operation).

CLAUSE FORMATS:
• User Email: 'user@endor.ai', 'tgowan@endor.ai'
• Domain Wildcard: '*@endor.ai' (all users from domain)
• Identity Provider UUID: '68fae83022a47bdae812bb42' (all users from this IDP)
• API Key: 'endr+abCdefGhIJKL0PQrs' with 'api-key' # endorctl:allow
• Group Claims: 'group=developers', 'group=admins'
• Mixed: 'tgowan@endor.ai,68fae83022a47bdae812bb42' (user + IDP)

SECURITY: All clauses must match (AND logic) for policy to apply.""",
    )
    target_namespaces: List[str] = Field(
        ...,
        description="Target namespaces - list of namespaces where this policy applies (must be current namespace or its children)",
    )
    propagate: bool = Field(
        default=False,
        description="Propagation flag - whether policy should apply to child namespaces of target namespaces",
    )
    permissions: AuthorizationPolicyPermissions = Field(
        ...,
        description="Permissions configuration - defines what actions are allowed",
    )
    expiration_time: Optional[str] = Field(
        None,
        description="Expiration time - ISO 8601 datetime when policy expires (optional, defaults to never expire)",
    )
    is_support_policy: Optional[bool] = Field(
        None,
        description="Indicates that the policy is a support policy and cannot be altered without using the SupportAccess API (read-only)",
    )

    @field_validator("clause")
    @classmethod
    def validate_clause(cls, v: List[str]) -> List[str]:
        """Validate clause strings are not empty and match allowed pattern."""
        if not v:
            raise ValueError("clause cannot be empty")
        validated = []
        for clause in v:
            if not clause.strip():
                raise ValueError("clause items cannot be empty or whitespace")
            # Pattern: letters, numbers, and =@._-/: +()&
            validated.append(clause.strip())
        return validated

    @field_validator("target_namespaces")
    @classmethod
    def validate_target_namespaces(cls, v: List[str]) -> List[str]:
        """Validate target namespaces are not empty strings."""
        if not v:
            raise ValueError("target_namespaces cannot be empty")
        return [ns.strip() for ns in v if ns.strip()]


class AuthorizationPolicyMeta(BaseMeta):
    """Authorization policy metadata extending BaseMeta."""

    # Authorization policy-specific fields only (universal fields inherited from BaseMeta)
    pass

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate authorization policy name is not empty or whitespace."""
        if not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate authorization policy description."""
        if v is not None and not v.strip():
            raise ValueError("description cannot be empty or whitespace")
        return v.strip() if v else v


class AuthorizationPolicy(BaseResource):
    """
    Authorization Policy resource model extending BaseResource.

    OPERATION SUPPORT:
    ==================
    ✅ GET: List authorization policies, Get by UUID
    ✅ POST: Create new authorization policies
    ✅ PATCH: Update existing authorization policies
    ✅ DELETE: Delete authorization policies

    FIELD MUTABILITY:
    =================
    IMMUTABLE FIELDS (read-only, system-managed):
    - uuid: Unique identifier
    - meta.create_time, meta.created_by: Creation metadata
    - meta.update_time, meta.updated_by: Auto-managed timestamps
    - spec.is_support_policy: Support policy flag (read-only)
    - tenant_meta.namespace: Namespace assignment

    MUTABLE FIELDS (can be updated via PATCH):
    - meta.name: Policy name
    - meta.description: Policy description
    - meta.tags: Policy tags
    - spec.clause: Authorization clauses
    - spec.target_namespaces: Target namespaces
    - spec.propagate: Propagation flag
    - spec.permissions: Permissions configuration
    - spec.expiration_time: Expiration time
    - propagate: Whether to propagate to child namespaces

    FEATURES:
    =========
    - System role-based permissions (ADMIN, READ_ONLY, CODE_SCANNER, etc.)
    - Resource-specific permission rules
    - Authorization clause matching with AND logic
    - Namespace targeting and propagation
    - Expiration time support
    """

    # Authorization policy-specific fields (universal fields inherited from BaseResource)
    spec: Optional[AuthorizationPolicySpec] = Field(
        None, description="Authorization policy specification"
    )  # type: ignore

    model_config = {"extra": "ignore"}

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift in authorization policy responses."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "clause",
                "target_namespaces",
                "propagate",
                "permissions",
                "expiration_time",
                "is_support_policy",
            }

            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )

        return v


class CreateAuthorizationPolicyPayload(BaseModel):
    """Payload for creating a new authorization policy."""

    meta: AuthorizationPolicyMeta = Field(
        ..., description="Authorization policy metadata"
    )
    spec: AuthorizationPolicySpec = Field(
        ..., description="Authorization policy specification"
    )
    propagate: Optional[bool] = Field(
        True, description="Propagate to child namespaces"
    )


class UpdateAuthorizationPolicyPayload(BaseModel):
    """
    Payload for updating an Endor Labs authorization policy.

    MUTABLE FIELDS (can be updated via PATCH):
    - meta.name: Policy name
    - meta.description: Policy description
    - meta.tags: Policy tags
    - spec.clause: Authorization clauses
    - spec.target_namespaces: Target namespaces
    - spec.propagate: Propagation flag
    - spec.permissions: Permissions configuration
    - spec.expiration_time: Expiration time
    - propagate: Whether to propagate to child namespaces

    IMMUTABLE FIELDS (read-only, managed by API):
    - uuid: Unique identifier
    - meta.create_time, meta.created_by: Creation metadata
    - meta.update_time, meta.updated_by: Auto-managed timestamps
    - spec.is_support_policy: Support policy flag (read-only)
    - tenant_meta.namespace: Namespace assignment

    Example:
        >>> payload = UpdateAuthorizationPolicyPayload(
        ...     meta=AuthorizationPolicyMeta(
        ...         name="Updated Policy Name",
        ...         description="Updated description"
        ...     ),
        ...     spec=AuthorizationPolicySpec(
        ...         clause=["user@endor.ai"],
        ...         target_namespaces=["namespace"],
        ...         propagate=False,
        ...         permissions=AuthorizationPolicyPermissions(
        ...             roles=["SYSTEM_ROLE_READ_ONLY"]
        ...         )
        ...     )
        ... )
        >>> policy = update_authorization_policy(
        ...     client, namespace, uuid, payload
        ... )
    """

    meta: Optional[AuthorizationPolicyMeta] = Field(
        None, description="Updated authorization policy metadata"
    )
    spec: Optional[AuthorizationPolicySpec] = Field(
        None, description="Updated authorization policy specification"
    )
    propagate: Optional[bool] = Field(
        None, description="Propagate to child namespaces"
    )


def list_authorization_policies(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
    **kwargs,
) -> List[AuthorizationPolicy]:
    """
    List all authorization policies in a namespace with filtering support.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        list_params: Optional list parameters for filtering, masking, pagination
        **kwargs: Additional query parameters

    Returns:
        List of AuthorizationPolicy objects
    """
    ops = _get_authorization_policy_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)  # type: ignore


def get_authorization_policy(
    client: APIClient,
    tenant_meta_namespace: str,
    policy_uuid: str,
) -> Optional[AuthorizationPolicy]:
    """
    Get a specific authorization policy by UUID.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        policy_uuid: Authorization policy UUID

    Returns:
        AuthorizationPolicy object or None if not found
    """
    ops = _get_authorization_policy_ops(client)
    return ops.get(tenant_meta_namespace, policy_uuid)  # type: ignore


def create_authorization_policy(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateAuthorizationPolicyPayload,
) -> Optional[AuthorizationPolicy]:
    """
    Create a new authorization policy in a namespace.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        payload: Authorization policy creation payload

    Returns:
        Created AuthorizationPolicy object or None if creation failed
    """
    try:
        request_data = {
            "meta": payload.meta.model_dump(),
            "spec": payload.spec.model_dump(),
            "propagate": payload.propagate,
        }

        res = client.post(
            f"v1/namespaces/{tenant_meta_namespace}/authorization-policies",
            json=request_data,
        )
        data = res.json()
        return AuthorizationPolicy(**data)

    except Exception as e:
        logger.error(
            f"Error creating authorization policy: {e}", exc_info=True
        )
        return None


def update_authorization_policy(
    client: APIClient,
    tenant_meta_namespace: str,
    policy_uuid: str,
    payload: UpdateAuthorizationPolicyPayload,
    update_mask: Optional[str] = None,
) -> Optional[AuthorizationPolicy]:
    """
    Update an existing authorization policy using partial updates.

    This function supports updating only specific fields using the update_mask
    parameter, which enables efficient partial updates without overwriting
    unchanged fields.

    IMPORTANT: Only authorization policies created in the current namespace can
    be updated. Policies inherited from parent namespaces are immutable and
    will return 404 errors when attempting to update.

    MUTABLE FIELDS (for policies created in current namespace):
    - meta.name: Policy name
    - meta.description: Policy description
    - meta.tags: Policy tags
    - spec.clause: Authorization clauses
    - spec.target_namespaces: Target namespaces
    - spec.propagate: Propagation flag
    - spec.permissions: Permissions configuration
    - spec.expiration_time: Expiration time
    - propagate: Whether to propagate to child namespaces

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        policy_uuid: Authorization policy UUID
        payload: Authorization policy update payload
        update_mask: Optional comma-separated list of fields to update
            (e.g., "meta.name,spec.clause"). If provided, only these
            fields will be updated. If omitted, all non-None fields in
            payload will be updated.

    Returns:
        Updated AuthorizationPolicy object or None if update failed

    Raises:
        requests.exceptions.HTTPError: For API-level errors (403, 404, etc.)
        pydantic.ValidationError: If response data doesn't match expected schema

    Example:
        >>> # Update policy name and description
        >>> payload = UpdateAuthorizationPolicyPayload(
        ...     meta=AuthorizationPolicyMeta(
        ...         name="Updated Policy",
        ...         description="Updated description"
        ...     )
        ... )
        >>> policy = update_authorization_policy(
        ...     client, namespace, uuid, payload, "meta.name,meta.description"
        ... )

        >>> # Update permissions
        >>> payload = UpdateAuthorizationPolicyPayload(
        ...     spec=AuthorizationPolicySpec(
        ...         clause=["user@endor.ai"],
        ...         target_namespaces=["namespace"],
        ...         propagate=False,
        ...         permissions=AuthorizationPolicyPermissions(
        ...             roles=["SYSTEM_ROLE_ADMIN"]
        ...         )
        ...     )
        ... )
        >>> policy = update_authorization_policy(
        ...     client, namespace, uuid, payload, "spec.permissions"
        ... )
    """
    try:
        # Get the current policy to include required fields
        current_policy = get_authorization_policy(
            client, tenant_meta_namespace, policy_uuid
        )
        if not current_policy:
            logger.error(f"Authorization policy {policy_uuid} not found")
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
                    **current_policy.spec.model_dump(),  # Include all existing spec fields
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

        logger.info(
            f"Updating authorization policy {policy_uuid} with mask: {update_mask}"
        )

        res = client.patch(
            f"v1/namespaces/{tenant_meta_namespace}/authorization-policies",
            json=request_data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        data = res.json()
        return AuthorizationPolicy(**data)

    except Exception as e:
        logger.error(
            f"Error updating authorization policy {policy_uuid}: {e}",
            exc_info=True,
        )
        return None


def delete_authorization_policy(
    client: APIClient,
    tenant_meta_namespace: str,
    policy_uuid: str,
) -> bool:
    """
    Delete an authorization policy.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        policy_uuid: Authorization policy UUID

    Returns:
        True if deletion successful, False otherwise
    """
    try:
        res = client.delete(
            f"v1/namespaces/{tenant_meta_namespace}/authorization-policies/{policy_uuid}"
        )
        return res.status_code == 200

    except Exception as e:
        logger.error(
            f"Error deleting authorization policy {policy_uuid}: {e}",
            exc_info=True,
        )
        return False


# Convenience functions for common filtering patterns
def list_authorization_policies_by_role(
    client: APIClient,
    tenant_meta_namespace: str,
    role: SystemRole,
) -> List[AuthorizationPolicy]:
    """List authorization policies filtered by system role."""
    list_params = ListParameters(
        filter=f"spec.permissions.roles=={role.value}",
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
    return list_authorization_policies(
        client, tenant_meta_namespace, list_params=list_params
    )


def list_authorization_policies_by_namespace(
    client: APIClient,
    tenant_meta_namespace: str,
    target_namespace: str,
) -> List[AuthorizationPolicy]:
    """List authorization policies filtered by target namespace."""
    list_params = ListParameters(
        filter=f"spec.target_namespaces=={target_namespace}",
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
    return list_authorization_policies(
        client, tenant_meta_namespace, list_params=list_params
    )


def list_authorization_policies_with_mask(
    client: APIClient,
    tenant_meta_namespace: str,
    fields: List[str],
) -> List[AuthorizationPolicy]:
    """List authorization policies with field masking."""
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
    return list_authorization_policies(
        client, tenant_meta_namespace, list_params=list_params
    )


def list_authorization_policies_paginated(
    client: APIClient,
    tenant_meta_namespace: str,
    page_size: int = 10,
    page_token: Optional[str] = None,
) -> List[AuthorizationPolicy]:
    """List authorization policies with pagination."""
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
    return list_authorization_policies(
        client, tenant_meta_namespace, list_params=list_params
    )


def list_authorization_policies_sorted(
    client: APIClient,
    tenant_meta_namespace: str,
    sort_field: str = "meta.create_time",
    desc: bool = True,
) -> List[AuthorizationPolicy]:
    """List authorization policies with sorting."""
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
    return list_authorization_policies(
        client, tenant_meta_namespace, list_params=list_params
    )

