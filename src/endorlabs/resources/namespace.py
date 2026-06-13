"""Namespace — thin consumer wrapper over generated V1Namespace."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from endorlabs.generated.models.namespace_service import (
    V1Namespace,
)

from .base import BaseMeta, BaseSpec
from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class Namespace(V1Namespace, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for Namespace (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("Namespace")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("Namespace")


# --- integration / create-update compat (pre-cutover helpers) ---


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


class ConsumerNamespaceSpec(BaseSpec):
    """Namespace specification extending BaseSpec."""

    full_name: str | None = Field(
        None,
        description="Fully qualified namespace name (read-only).",
    )
    managed: bool | None = Field(
        None,
        description="Whether the namespace is managed (read-only).",
    )


NamespaceSpec = ConsumerNamespaceSpec


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


def build_create_payload(**kwargs: Any) -> CreateNamespacePayload:
    """Build CreateNamespacePayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateNamespacePayload, kwargs, attr_name="Namespace"
    )
