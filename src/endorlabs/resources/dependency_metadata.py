"""DependencyMetadata — thin facade over generated V1DependencyMetadata.

Tenant-scoped importer-to-dependency rows. Update is not exposed on the facade.
``spec.dependency_data.namespace`` may be ``oss`` for catalog coordinates only.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.dependency_metadata_service import (
    V1DependencyMetadata,
)
from endorlabs.generated.models.dependency_metadata_service import (
    V1DependencyMetadataSpec as _V1DependencyMetadataSpec,
)

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import (
    ConsumerContext,
    ConsumerResourceWireMixin,
    partial_spec_model,
)

DependencyMetadataSpec = partial_spec_model(
    _V1DependencyMetadataSpec, name="DependencyMetadataSpec"
)


class DependencyMetadata(
    V1DependencyMetadata, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Facade model for DependencyMetadata (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("DependencyMetadata")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("DependencyMetadata")

    spec: DependencyMetadataSpec | None = None  # pyright: ignore[reportIncompatibleVariableOverride]
    context: ConsumerContext | None = None  # pyright: ignore[reportIncompatibleVariableOverride]


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
