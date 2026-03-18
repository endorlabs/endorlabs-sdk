"""Authorization Policy resource module for Endor Labs API.

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

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, override

from pydantic import BaseModel, Field, field_validator

from ..core.types import ListParameters
from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
    FlexibleEnum,
)
from ..operations import BaseResourceOperations
from ..utils.logging_config import get_resource_logger

if TYPE_CHECKING:
    from ..api_client import APIClient

logger = get_resource_logger(__name__)


class SystemRole(FlexibleEnum):
    """System role enumeration for authorization policies."""

    UNSPECIFIED = "SYSTEM_ROLE_UNSPECIFIED"
    ADMIN = "SYSTEM_ROLE_ADMIN"
    CODE_SCANNER = "SYSTEM_ROLE_CODE_SCANNER"
    ENDOR_PATCHING = "SYSTEM_ROLE_ENDOR_PATCHING"
    ENDOR_PROXY = "SYSTEM_ROLE_ENDOR_PROXY"  # Deprecated
    ONPREM_SCHEDULER = "SYSTEM_ROLE_ONPREM_SCHEDULER"
    PACKAGE_FIREWALL = "SYSTEM_ROLE_PACKAGE_FIREWALL"
    POLICY_EDITOR = "SYSTEM_ROLE_POLICY_EDITOR"
    READ_ONLY = "SYSTEM_ROLE_READ_ONLY"
    SYNC_ORG = "SYSTEM_ROLE_SYNC_ORG"


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

    methods: list[str] = Field(
        ...,
        description="Array of allowed methods (e.g., ['METHOD_READ', 'METHOD_CREATE'])",
    )


class AuthorizationPolicyPermissions(BaseModel):
    """Permissions configuration for authorization policy."""

    roles: list[str] | None = Field(
        None,
        description=(
            "System roles - predefined role-based permissions "
            "(e.g., SYSTEM_ROLE_READ_ONLY, SYSTEM_ROLE_ADMIN)"
        ),
    )
    rules: dict[str, dict[str, list[str]]] | None = Field(
        None,
        description=(
            "Resource-specific permissions - maps resource types to allowed "
            "methods (e.g., {'repository': {'methods': "
            "['METHOD_READ', 'METHOD_CREATE']}})"
        ),
    )
    except_resources: list[str] | None = Field(
        None,
        description=(
            "Excluded resources - list of resources to exclude from "
            "wildcard permissions"
        ),
    )

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, v: list[str] | None) -> list[str] | None:
        """Validate roles are not empty strings."""
        if v:
            return [role.strip() for role in v if role.strip()]
        return v

    @field_validator("except_resources")
    @classmethod
    def validate_except_resources(cls, v: list[str] | None) -> list[str] | None:
        """Validate except_resources are not empty strings."""
        if v:
            return [resource.strip() for resource in v if resource.strip()]
        return v


class AuthorizationPolicySpec(BaseSpec):
    """Authorization policy specification extending BaseSpec."""

    clause: list[str] = Field(
        ...,
        description=(
            "Authorization clauses - list of claims that must match "
            "(AND operation).\n\n"
            "CLAUSE FORMATS:\n"
            "• User Email: 'user@endor.ai', 'tgowan@endor.ai'\n"
            "• Domain Wildcard: '*@endor.ai' (all users from domain)\n"
            "• Identity Provider UUID: '68fae83022a47bdae812bb42' "
            "(all users from this IDP)\n"
            "• API Key: 'endr+abCdefGhIJKL0PQrs' with 'api-key' "
            "# endorctl:allow\n"
            "• Group Claims: 'group=developers', 'group=admins'\n"
            "• Mixed: 'tgowan@endor.ai,68fae83022a47bdae812bb42' "
            "(user + IDP)\n\n"
            "SECURITY: All clauses must match (AND logic) for policy to apply."
        ),
    )
    target_namespaces: list[str] = Field(
        ...,
        description=(
            "Target namespaces - list of namespaces where this policy "
            "applies (must be current namespace or its children)"
        ),
    )
    propagate: bool = Field(
        default=False,
        description=(
            "Propagation flag - whether policy should apply to child "
            "namespaces of target namespaces"
        ),
    )
    permissions: AuthorizationPolicyPermissions = Field(
        ...,
        description="Permissions configuration - defines what actions are allowed",
    )
    expiration_time: str | None = Field(
        None,
        description=(
            "Expiration time - ISO 8601 datetime when policy expires "
            "(optional, defaults to never expire)"
        ),
    )
    is_support_policy: bool | None = Field(
        None,
        description=(
            "Indicates that the policy is a support policy and cannot be "
            "altered without using the SupportAccess API (read-only)"
        ),
    )

    @field_validator("clause")
    @classmethod
    def validate_clause(cls, v: list[str]) -> list[str]:
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
    def validate_target_namespaces(cls, v: list[str]) -> list[str]:
        """Validate target namespaces are not empty strings."""
        if not v:
            raise ValueError("target_namespaces cannot be empty")
        return [ns.strip() for ns in v if ns.strip()]


class AuthorizationPolicyMeta(BaseMeta):
    """Authorization policy metadata extending BaseMeta."""

    # Authorization policy-specific fields only
    # (universal fields inherited from BaseMeta)
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
    def validate_description(cls, v: str | None) -> str | None:
        """Validate authorization policy description."""
        if v is not None and not v.strip():
            raise ValueError("description cannot be empty or whitespace")
        return v.strip() if v else v


class AuthorizationPolicy(BaseResource):
    """Authorization Policy resource model extending BaseResource.

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

    # Authorization policy-specific fields
    # (universal fields inherited from BaseResource)
    spec: AuthorizationPolicySpec | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Authorization policy specification"
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "ignore"}

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
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
                    "Schema drift detected in %s: unknown fields %s",
                    info.field_name,
                    unknown_fields,
                )

        return v

    @override
    @classmethod
    def get_mutable_fields_cls(cls) -> list[str]:
        """Get list of mutable fields for AuthorizationPolicy."""
        return [
            "meta.name",
            "meta.description",
            "meta.tags",
            "spec",
            "propagate",
        ]

    @override
    @classmethod
    def get_immutable_fields_cls(cls) -> list[str]:
        """Get list of immutable fields for AuthorizationPolicy."""
        return [
            "uuid",
            "meta.create_time",
            "meta.created_by",
            "meta.update_time",
            "meta.updated_by",
            "meta.upsert_time",
            "meta.kind",
            "meta.version",
            "meta.references",
            "meta.index_data",
            "tenant_meta.namespace",
            "spec.is_support_policy",
        ]


class CreateAuthorizationPolicyPayload(BaseModel):
    """Payload for creating a new authorization policy."""

    meta: AuthorizationPolicyMeta = Field(
        ..., description="Authorization policy metadata"
    )
    spec: AuthorizationPolicySpec = Field(
        ..., description="Authorization policy specification"
    )
    propagate: bool | None = Field(True, description="Propagate to child namespaces")


def build_create_payload(**kwargs: Any) -> CreateAuthorizationPolicyPayload:
    """Build CreateAuthorizationPolicyPayload from kwargs (decoupled create)."""
    return CreateAuthorizationPolicyPayload(**kwargs)


class UpdateAuthorizationPolicyPayload(BaseModel):
    """Payload for updating an Endor Labs authorization policy.

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

    meta: AuthorizationPolicyMeta | None = Field(
        None, description="Updated authorization policy metadata"
    )
    spec: AuthorizationPolicySpec | None = Field(
        None, description="Updated authorization policy specification"
    )
    propagate: bool | None = Field(None, description="Propagate to child namespaces")


# Convenience functions for common filtering patterns
def list_authorization_policies_by_role(
    client: APIClient,
    tenant_meta_namespace: str,
    role: SystemRole,
) -> list[AuthorizationPolicy]:
    """List authorization policies filtered by system role."""
    list_params = ListParameters(  # pyright: ignore[reportCallIssue]
        filter=f"spec.permissions.roles=={role.value}",
    )
    ops = BaseResourceOperations(client, "authorization-policies", AuthorizationPolicy)
    return ops.list(tenant_meta_namespace, list_params)


def list_authorization_policies_by_namespace(
    client: APIClient,
    tenant_meta_namespace: str,
    target_namespace: str,
) -> list[AuthorizationPolicy]:
    """List authorization policies filtered by target namespace."""
    list_params = ListParameters(  # pyright: ignore[reportCallIssue]
        filter=f"spec.target_namespaces=={target_namespace}",
    )
    ops = BaseResourceOperations(client, "authorization-policies", AuthorizationPolicy)
    return ops.list(tenant_meta_namespace, list_params)


def list_authorization_policies_paginated(
    client: APIClient,
    tenant_meta_namespace: str,
    page_size: int = 10,
    page_token: str | None = None,
) -> list[AuthorizationPolicy]:
    """List authorization policies with pagination."""
    list_params = ListParameters(  # pyright: ignore[reportCallIssue]
        page_size=page_size,
        page_token=page_token,
    )
    ops = BaseResourceOperations(client, "authorization-policies", AuthorizationPolicy)
    return ops.list(tenant_meta_namespace, list_params)


def list_authorization_policies_sorted(
    client: APIClient,
    tenant_meta_namespace: str,
    sort_by: str = "meta.create_time",
    desc: bool = True,
) -> list[AuthorizationPolicy]:
    """List authorization policies with sorting."""
    list_params = ListParameters(  # pyright: ignore[reportCallIssue]
        sort_by=sort_by,
        desc=desc,
    )
    ops = BaseResourceOperations(client, "authorization-policies", AuthorizationPolicy)
    return ops.list(tenant_meta_namespace, list_params)
