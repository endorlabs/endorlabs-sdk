"""APIKey resource module for Endor Labs API.

This module provides comprehensive API key management capabilities including
listing, examining, creating, and deleting API keys.

API OPERATIONS SUPPORTED:
- GET: List API keys, Get API key by UUID
- POST: Create new API keys
- DELETE: Delete API keys

API FEATURES:
- Full CRUD operations supported (except UPDATE - API keys cannot be updated)
- System role-based permissions (ADMIN, READ_ONLY, CODE_SCANNER, etc.)
- Resource-specific permission rules
- Expiration time support
- Namespace propagation control
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator

from ..api_client import APIClient
from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseResourceOperations,
    BaseSpec,
)
from ..types import ListParameters

logger = logging.getLogger(__name__)


# Global resource instance
def _get_api_key_ops(client: APIClient) -> BaseResourceOperations[APIKey]:
    """Get BaseResourceOperations instance for API keys."""
    return BaseResourceOperations(client, "api-keys", APIKey)


class PermissionsMethods(BaseModel):
    """Methods configuration for resource permissions."""

    methods: list[str] = Field(
        ...,
        description=(
            "Array of allowed methods (e.g., ['METHOD_READ', 'METHOD_CREATE'])"
        ),
    )


class APIKeyPermissions(BaseModel):
    """Permissions configuration for API key."""

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
            "Resource-specific permissions - maps resource types to "
            "allowed methods (e.g., {'scan_profile': "
            "{'methods': ['METHOD_READ', 'METHOD_CREATE']}})"
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


class APIKeySpec(BaseSpec):
    """API key specification extending BaseSpec."""

    key: str | None = Field(
        None,
        description="The identifier of an API key (read-only, returned by API)",
    )
    secret: str | None = Field(
        None,
        description=(
            "The secret for the specified API key (read-only, returned by API)"
        ),
    )
    permissions: APIKeyPermissions = Field(
        ...,
        description="The access permissions associated with the API key",
    )
    expiration_time: str = Field(
        ...,
        description="The expiration time of the API key (ISO 8601 datetime)",
    )
    issuing_user: dict[str, Any] | None = Field(
        None,
        description=("The user that created this API key (read-only, returned by API)"),
    )


class APIKeyMeta(BaseMeta):
    """API key metadata extending BaseMeta."""

    # API key-specific fields only (universal fields inherited from BaseMeta)
    pass

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate API key name is not empty or whitespace."""
        if not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Validate API key description."""
        if v is not None and not v.strip():
            raise ValueError("description cannot be empty or whitespace")
        return v.strip() if v else v


class APIKey(BaseResource):
    """API Key resource model extending BaseResource.

    OPERATION SUPPORT:
    ==================
    ✅ GET: List API keys, Get by UUID
    ✅ POST: Create new API keys
    ❌ PATCH: API keys cannot be updated (immutable after creation)
    ✅ DELETE: Delete API keys

    FIELD MUTABILITY:
    =================
    IMMUTABLE FIELDS (read-only, system-managed):
    - uuid: Unique identifier
    - meta.create_time, meta.created_by: Creation metadata
    - meta.update_time, meta.updated_by: Auto-managed timestamps
    - spec.key: API key identifier (returned on creation)
    - spec.secret: API key secret (returned on creation, only shown once)
    - spec.issuing_user: User that created the key
    - tenant_meta.namespace: Namespace assignment

    MUTABLE FIELDS (set at creation only, cannot be updated):
    - meta.name: API key name
    - meta.description: API key description
    - meta.tags: API key tags
    - spec.permissions: Permissions configuration
    - spec.expiration_time: Expiration time
    - propagate: Whether to propagate to child namespaces

    FEATURES:
    =========
    - System role-based permissions (ADMIN, READ_ONLY, CODE_SCANNER, etc.)
    - Resource-specific permission rules
    - Expiration time support
    - Namespace propagation control
    - Credentials (key/secret) returned only on creation
    """

    # API key-specific fields (universal fields inherited from BaseResource)
    spec: APIKeySpec | None = Field(None, description="API key specification")  # type: ignore

    model_config: ClassVar[dict[str, str]] = {"extra": "ignore"}

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift in API key responses."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "key",
                "secret",
                "permissions",
                "expiration_time",
                "issuing_user",
            }

            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )

        return v


class CreateAPIKeyPayload(BaseModel):
    """Payload for creating a new API key."""

    meta: APIKeyMeta = Field(..., description="API key metadata")
    spec: APIKeySpec = Field(..., description="API key specification")
    propagate: bool | None = Field(False, description="Propagate to child namespaces")


def list_api_keys(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    **kwargs: Any,
) -> list[APIKey]:
    """List API keys in the specified namespace.

    Args:
        client: Authenticated APIClient instance
        tenant_meta_namespace: Target tenant namespace (canonical name)
        list_params: Optional list parameters for filtering/pagination
        **kwargs: Additional query parameters

    Returns:
        List of APIKey resources

    Example:
        >>> from endor_cockpit.api_client import APIClient
        >>> client = APIClient()
        >>> api_keys = list_api_keys(client, "tenant.namespace")
        >>> for key in api_keys:
        ...     print(f"{key.meta.name}: {key.uuid}")

    """
    ops = _get_api_key_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)


def get_api_key(
    client: APIClient, tenant_meta_namespace: str, api_key_uuid: str
) -> APIKey:
    """Get an API key by UUID.

    Args:
        client: Authenticated APIClient instance
        tenant_meta_namespace: Target tenant namespace (canonical name)
        api_key_uuid: UUID of the API key

    Returns:
        APIKey resource

    Raises:
        NotFoundError: If API key doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    Example:
        >>> from endor_cockpit.api_client import APIClient
        >>> client = APIClient()
        >>> api_key = get_api_key(client, "tenant.namespace", "uuid-here")
        >>> print(f"Key: {api_key.meta.name}")

    """
    ops = _get_api_key_ops(client)
    return ops.get(tenant_meta_namespace, api_key_uuid)


def create_api_key(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateAPIKeyPayload,
) -> APIKey:
    """Create a new API key with pre-validation and typed errors.

    Args:
        client: Authenticated APIClient instance
        tenant_meta_namespace: Target tenant namespace (canonical name)
        payload: API key creation payload

    Returns:
        Created APIKey resource with key and secret in spec

    Raises:
        ValidationError: If payload is invalid
        NotFoundError: If namespace doesn't exist
        PermissionDeniedError: If user lacks permission
        ConflictError: If API key already exists
        ServerError: If server error occurs

    Example:
        >>> from endor_cockpit.api_client import APIClient
        >>> from datetime import datetime, timedelta
        >>> from endor_cockpit.resources.api_key import (
        ...     CreateAPIKeyPayload, APIKeyMeta, APIKeySpec, APIKeyPermissions
        ... )
        >>> client = APIClient()
        >>> expiration = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        >>> payload = CreateAPIKeyPayload(
        ...     meta=APIKeyMeta(name="My API Key", description="Test key"),
        ...     spec=APIKeySpec(
        ...         permissions=APIKeyPermissions(
        ...             roles=["SYSTEM_ROLE_READ_ONLY"]
        ...         ),
        ...         expiration_time=expiration
        ...     )
        ... )
        >>> api_key = create_api_key(client, "tenant.namespace", payload)
        >>> print(f"Key: {api_key.spec.key}")
        >>> print(f"Secret: {api_key.spec.secret}")

    """
    ops = _get_api_key_ops(client)
    return ops.create(tenant_meta_namespace, payload)


def delete_api_key(
    client: APIClient, tenant_meta_namespace: str, api_key_uuid: str
) -> bool:
    """Delete an API key by UUID.

    Args:
        client: Authenticated APIClient instance
        tenant_meta_namespace: Target tenant namespace (canonical name)
        api_key_uuid: UUID of the API key to delete

    Returns:
        True if deletion succeeded, False otherwise

    Example:
        >>> from endor_cockpit.api_client import APIClient
        >>> client = APIClient()
        >>> success = delete_api_key(client, "tenant.namespace", "uuid-here")
        >>> if success:
        ...     print("API key deleted successfully")

    """
    ops = _get_api_key_ops(client)
    return ops.delete(tenant_meta_namespace, api_key_uuid)
