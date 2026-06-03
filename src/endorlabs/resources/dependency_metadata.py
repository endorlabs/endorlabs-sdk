"""DependencyMetadata — thin facade over generated V1DependencyMetadata.

Tenant-scoped importer-to-dependency rows. Update is not exposed on the facade.
``spec.dependency_data.namespace`` may be ``oss`` for catalog coordinates only.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.dependency_metadata_service import V1DependencyMetadata


class DependencyMetadata(V1DependencyMetadata):
    """Facade model for DependencyMetadata (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = [
        "meta.description",
        "meta.name",
        "meta.tags",
        "spec",
    ]
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = [
        "meta.create_time",
        "meta.created_by",
        "meta.index_data",
        "meta.kind",
        "meta.references",
        "meta.update_time",
        "meta.updated_by",
        "meta.upsert_time",
        "meta.version",
        "tenant_meta.namespace",
        "uuid",
    ]

    @classmethod
    def get_mutable_fields_cls(cls) -> list[str]:
        """Return mutable field paths for updates."""
        return list(cls._MUTABLE_FIELDS)

    @classmethod
    def get_immutable_fields_cls(cls) -> list[str]:
        """Return read-only field paths."""
        return list(cls._IMMUTABLE_FIELDS)


class CreateDependencyMetadataPayload(BaseModel):
    """Create payload for DependencyMetadata."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)


def build_create_payload(**kwargs: Any) -> CreateDependencyMetadataPayload:
    """Build create payload for DependencyMetadata."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateDependencyMetadataPayload, kwargs, attr_name="DependencyMetadata"
    )
