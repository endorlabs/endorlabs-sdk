"""AuthorizationPolicy — thin consumer wrapper over generated V1AuthorizationPolicy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, cast

from pydantic import BaseModel, Field, field_validator

from endorlabs.core.types import ListParameters
from endorlabs.generated.models.authorization_policy_service import (
    V1AuthorizationPolicy,
)
from endorlabs.operations import BaseResourceOperations

from .base import BaseMeta, BaseSpec, FlexibleEnum
from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin

if TYPE_CHECKING:
    from ..api_client import APIClient


class AuthorizationPolicy(
    V1AuthorizationPolicy, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for AuthorizationPolicy (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("AuthorizationPolicy")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("AuthorizationPolicy")


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
    rows = ops.list(tenant_meta_namespace, list_params)
    return cast("list[AuthorizationPolicy]", rows)


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
    rows = ops.list(tenant_meta_namespace, list_params)
    return cast("list[AuthorizationPolicy]", rows)


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
    rows = ops.list(tenant_meta_namespace, list_params)
    return cast("list[AuthorizationPolicy]", rows)


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
    rows = ops.list(tenant_meta_namespace, list_params)
    return cast("list[AuthorizationPolicy]", rows)


# --- integration / create-update compat (pre-cutover helpers) ---


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
            "• User Email: 'user@example.com', 'admin@example.com'\n"
            "• Domain Wildcard: '*@example.com' (all users from domain)\n"
            "• Identity Provider UUID: '0123456789abcdef01234567' "
            "(all users from this IDP)\n"
            "• API Key: 'my-service-credential' with claim 'api-key'\n"
            "• Group Claims: 'group=developers', 'group=admins'\n"
            "• Mixed: 'admin@example.com,0123456789abcdef01234567' "
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


class CreateAuthorizationPolicyPayload(BaseModel):
    """Payload for creating a new authorization policy."""

    meta: AuthorizationPolicyMeta = Field(
        ..., description="Authorization policy metadata"
    )
    spec: AuthorizationPolicySpec = Field(
        ..., description="Authorization policy specification"
    )
    propagate: bool | None = Field(True, description="Propagate to child namespaces")


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
        ...         clause=["user@example.com"],
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


def build_create_payload(**kwargs: Any) -> CreateAuthorizationPolicyPayload:
    """Build CreateAuthorizationPolicyPayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateAuthorizationPolicyPayload, kwargs, attr_name="AuthorizationPolicy"
    )
