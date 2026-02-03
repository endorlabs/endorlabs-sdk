"""Namespace resource module for Endor Labs API.

This module provides CRUD operations for Namespace resources. Full CRUD
supported; update requires update_mask (e.g. meta.description). Canonical
naming: tenant.namespace.child.

API OPERATIONS SUPPORTED:
- GET: List namespaces, Get namespace by UUID
- POST: Create new namespaces
- PATCH: Update namespace metadata (update_mask required)
- DELETE: Delete namespaces

Full guide: docs/reference/namespace.md.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, override

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..exceptions import ValidationError as EndorValidationError
from ..models.base import BaseMeta, BaseResource, BaseResourceOperations, BaseSpec

if TYPE_CHECKING:
    from ..types import ListParameters

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


# Pydantic Models for Namespace data with OpenAPI validation
class NamespaceMeta(BaseMeta):
    """Metadata for an Endor Labs namespace extending BaseMeta.

    Namespace-specific fields only (universal fields inherited from BaseMeta).
    """

    # Namespace-specific fields (universal fields inherited from BaseMeta)
    pass  # No additional fields needed, all were universal

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that the name is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("name cannot be empty")
        return v


class NamespaceSpec(BaseSpec):
    """Namespace specification extending BaseSpec."""

    # Namespace-specific fields (universal fields inherited from BaseSpec)
    pass  # No additional fields needed for namespace spec


class NamespaceMetaCreate(BaseModel):
    """Metadata for creating an Endor Labs namespace."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="The name of the namespace"
    )
    description: str = Field(
        ..., min_length=1, description="Description of the namespace's purpose"
    )


class NamespaceMetaUpdate(BaseModel):
    """Metadata for updating an Endor Labs namespace."""

    description: str | None = Field(
        None, description="Updated description of the namespace's purpose"
    )


class UpdateNamespacePayload(BaseModel):
    """Payload for updating an Endor Labs namespace.

    MUTABLE FIELDS (can be updated via PATCH):
    - meta.description: Namespace description

    IMMUTABLE FIELDS (read-only, managed by API):
    - uuid: Unique identifier (set at creation)
    - meta.name: Namespace name (set at creation)
    - meta.create_time, meta.created_by: Creation metadata
    - meta.update_time, meta.updated_by: Auto-managed timestamps
    - meta.index_data: Index data (managed by API)
    - meta.kind: Resource kind (managed by API)
    - meta.version: Version (managed by API)

    Example:
        >>> payload = UpdateNamespacePayload(
        ...     meta=NamespaceMetaUpdate(description="Updated namespace description")
        ... )
        >>> ns = update_namespace(client, parent, uuid, payload, "meta.description")

    """

    meta: NamespaceMetaUpdate = Field(
        ..., description="Updated metadata for the namespace"
    )


class Namespace(BaseResource):
    """An Endor Labs namespace entity extending BaseResource.

    Namespace-specific fields (universal fields inherited from BaseResource).

    OPERATION SUPPORT:
    ==================
    ✅ GET: List namespaces, Get by UUID
    ✅ POST: Create new namespaces
    ✅ PATCH: Update namespace metadata
    ✅ DELETE: Delete namespaces

    FIELD MUTABILITY:
    =================
    IMMUTABLE FIELDS (read-only, system-managed):
    - uuid: Unique identifier
    - meta.name: Namespace name (set at creation)
    - meta.create_time, meta.created_by: Creation metadata
    - meta.update_time, meta.updated_by: Auto-managed timestamps
    - meta.index_data: Index data (managed by API)
    - meta.kind: Resource kind (managed by API)
    - meta.version: Version (managed by API)
    - tenant_meta.namespace: Namespace assignment

    MUTABLE FIELDS (can be updated via PATCH):
    - meta.description: Namespace description

    FEATURES:
    =========
    - Hierarchical namespace structure
    - Canonical naming (tenant.namespace.child)
    - Parent-child relationships
    - Tenant isolation
    - Full CRUD operations supported
    """

    # Namespace-specific fields (universal fields inherited from BaseResource)
    spec: NamespaceSpec = Field(..., description="Namespace specification")  # type: ignore

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data: Any) -> None:
        # Convert spec to NamespaceSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = NamespaceSpec(**data["spec"])
        super().__init__(**data)

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = set()  # No specific fields for namespace spec
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v

    @field_validator("uuid")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Validate that the UUID is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("uuid cannot be empty")
        return v


class CreateNamespacePayload(BaseModel):
    """Payload for creating a new namespace.

    Attributes:
        meta: Metadata for the new namespace

    """

    meta: NamespaceMetaCreate = Field(..., description="Metadata for the new namespace")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "meta": {
                    "name": "example-namespace",
                    "description": "An example namespace",
                }
            }
        }
    )


def build_create_payload(
    *,
    name: str,
    description: str,
) -> CreateNamespacePayload:
    """Build CreateNamespacePayload from kwargs (decoupled facade create)."""
    meta = NamespaceMetaCreate(name=name, description=description)
    return CreateNamespacePayload(meta=meta)


def _get_namespace_ops(client: APIClient) -> BaseResourceOperations[Namespace]:
    """Get BaseResourceOperations instance for namespaces."""
    return BaseResourceOperations(client, "namespaces", Namespace)


def list_namespaces(
    client: APIClient,
    tenant_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[Namespace]:
    """List all namespaces under the specified tenant namespace.

    Args:
        client: The APIClient instance to use for the request
        tenant_namespace: The parent namespace to list namespaces from
        list_params: Optional list parameters for filtering, pagination, etc.
        max_pages: Optional maximum number of pages to fetch.
            If None and in test environment, defaults to 10 pages max.
            If None in production, fetches all pages.
        **kwargs: Passed through to list implementation (e.g. filter, page_size).

    Returns:
        List[Namespace]: A list of Namespace objects. Empty list if error occurs.

    Raises:
        httpx.HTTPStatusError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema

    """
    ops = _get_namespace_ops(client)
    return ops.list(tenant_namespace, list_params, max_pages, **kwargs)


def list_namespaces_iter(
    client: APIClient,
    tenant_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[Namespace]:
    """Iterate over namespaces without materializing the full list."""
    ops = _get_namespace_ops(client)
    return ops.list_iter(tenant_namespace, list_params, max_pages, **kwargs)


def create_namespace(
    client: APIClient, tenant_meta_namespace: str, payload: CreateNamespacePayload
) -> Namespace:
    """Create a new namespace under the specified parent namespace.

    Uses pre-validation and typed errors.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The namespace under which to create the new namespace
        payload: The CreateNamespacePayload containing the new namespace details

    Returns:
        Namespace: The created Namespace object

    Raises:
        ValidationError: If payload is invalid
        NotFoundError: If parent namespace doesn't exist
        PermissionDeniedError: If user lacks permission
        ConflictError: If namespace already exists
        ServerError: If server error occurs

    """
    ops = _get_namespace_ops(client)
    return ops.create(tenant_meta_namespace, payload)


def get_namespace(
    client: APIClient, tenant_meta_namespace: str, namespace_uuid: str
) -> Namespace:
    """Retrieve a specific namespace by UUID.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The parent namespace containing the target namespace
        namespace_uuid: The UUID of the namespace to retrieve

    Returns:
        Namespace: The requested Namespace object

    Raises:
        NotFoundError: If namespace doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    ops = _get_namespace_ops(client)
    return ops.get(tenant_meta_namespace, namespace_uuid)


def delete_namespace(
    client: APIClient, tenant_meta_namespace: str, namespace_uuid: str
) -> bool:
    """Delete a namespace by UUID.

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The parent namespace containing the target namespace
        namespace_uuid: The UUID of the namespace to delete

    Returns:
        bool: True if deletion was successful, False otherwise

    Raises:
        httpx.HTTPStatusError: For API-level errors

    """
    ops = _get_namespace_ops(client)
    return ops.delete(tenant_meta_namespace, namespace_uuid)


def update_namespace(
    client: APIClient,
    tenant_meta_namespace: str,
    namespace_uuid: str,
    payload: UpdateNamespacePayload,
    update_mask: str,
) -> Namespace:
    """Update an existing namespace via collection PATCH with field mask.

    Uses the same pattern as other resources: collection URL, request body
    with ``object`` and ``request.update_mask``. The API requires at least
    one field in the update mask.

    MUTABLE FIELDS (include in update_mask):
    - meta.description: Namespace description
    - meta.name: Namespace name (per spec)
    - meta.tags: Namespace tags (per spec)
    - spec.managed: Managed flag (per spec)

    IMMUTABLE FIELDS (readOnly in API spec):
    - uuid, meta.create_time, meta.update_time, meta.created_by, meta.updated_by
    - meta.kind, meta.version, meta.references, meta.index_data
    - spec.full_name, tenant_meta.namespace

    Args:
        client: The APIClient instance to use for the request
        tenant_meta_namespace: The parent namespace containing the target namespace
        namespace_uuid: The UUID of the namespace to update
        payload: The UpdateNamespacePayload containing the updated namespace details
        update_mask: Comma-separated field paths to update (e.g. "meta.description").
            Required; the API returns 400 if no field mask is given.

    Returns:
        Namespace: The updated Namespace object

    Raises:
        ValidationError: If update_mask is missing or invalid, or API returns 400
            (e.g. "at least one fieldmask should be given")
        NotFoundError: If namespace doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    Example:
        >>> payload = UpdateNamespacePayload(
        ...     meta=NamespaceMetaUpdate(description="Updated description")
        ... )
        >>> updated = update_namespace(
        ...     client, parent, uuid, payload, "meta.description"
        ... )

    """
    if not (update_mask and update_mask.strip()):
        raise EndorValidationError(
            message=(
                "Namespace update requires an update_mask (e.g. 'meta.description'). "
                "The API requires at least one field mask."
            ),
            operation="update",
            namespace=tenant_meta_namespace,
            resource_uuid=namespace_uuid,
        )
    update_mask_list = [p.strip() for p in update_mask.split(",") if p.strip()]
    ops = _get_namespace_ops(client)
    logger.info(f"Updating namespace {namespace_uuid} with mask: {update_mask}")
    return ops.update(tenant_meta_namespace, namespace_uuid, payload, update_mask_list)


if __name__ == "__main__":
    # Note: To run this example, you need to be in the root of the project
    # and run as a module: python -m src.endor_sdk.resources.namespaces
    client = APIClient(max_retries=15, backoff_factor=1)

    tenant_namespace = "endor-solutions-tgowan"

    # Create mock namespaces using Pydantic models
    mock_namespaces_to_create = [
        CreateNamespacePayload(
            meta=NamespaceMetaCreate(
                name=f"mock-namespace-{i}",
                description=f"Description for mock-namespace-{i}",
            )
        )
        for i in range(3)
    ]

    for payload in mock_namespaces_to_create:
        print(f"Creating namespace: {payload.meta.name}")
        created_ns = create_namespace(client, tenant_namespace, payload)
        if created_ns:
            print(f"  -> Created with UUID: {created_ns.uuid}")

    # List and delete the created namespaces
    print("\nListing all namespaces to find and delete mocks...")
    all_namespaces = list_namespaces(client, tenant_namespace)
    mock_names = {p.meta.name for p in mock_namespaces_to_create}

    for ns in all_namespaces:
        if ns.meta.name in mock_names:
            print(f"Deleting namespace: {ns.meta.name} (UUID: {ns.uuid})")
            success = delete_namespace(client, tenant_namespace, ns.uuid)
            if success:
                print("  -> Deleted successfully.")
            else:
                print("  -> Deletion failed.")
