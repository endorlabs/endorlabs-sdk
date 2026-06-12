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

from typing import Any, override

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..utils.logging_config import get_resource_logger
from .base import BaseMeta, BaseResource, BaseSpec

logger = get_resource_logger(__name__)


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

    full_name: str | None = Field(
        None,
        description="Fully qualified namespace name (read-only).",
    )
    managed: bool | None = Field(
        None,
        description="Whether the namespace is managed (read-only).",
    )


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

    @field_validator("uuid")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Validate that the UUID is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("uuid cannot be empty")
        return v

    @override
    @classmethod
    def get_mutable_fields_cls(cls) -> list[str]:
        """Get list of mutable fields for Namespace."""
        return ["meta.description"]

    @override
    @classmethod
    def get_immutable_fields_cls(cls) -> list[str]:
        """Get list of immutable fields for Namespace."""
        return [
            "uuid",
            "meta.name",
            "meta.create_time",
            "meta.created_by",
            "meta.update_time",
            "meta.updated_by",
            "tenant_meta.namespace",
        ]


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
