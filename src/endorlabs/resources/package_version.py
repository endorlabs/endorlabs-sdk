"""PackageVersion — thin consumer wrapper over generated V1PackageVersion."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.package_version_service import (
    V1PackageVersion,
)
from endorlabs.generated.models.package_version_service import (
    V1PackageVersionSpec as _V1PackageVersionSpec,
)

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import (
    ConsumerContext,
    ConsumerResourceWireMixin,
    partial_spec_model,
)

PackageVersionSpec = partial_spec_model(
    _V1PackageVersionSpec, name="PackageVersionSpec"
)


class PackageVersion(
    V1PackageVersion, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for PackageVersion (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("PackageVersion")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("PackageVersion")

    spec: PackageVersionSpec | None = None  # pyright: ignore[reportIncompatibleVariableOverride]
    context: ConsumerContext | None = None  # pyright: ignore[reportIncompatibleVariableOverride]


class UpdatePackageVersionPayload(BaseModel):
    """Payload for updating PackageVersion resources."""

    meta: dict[str, Any] | None = None
    spec: dict[str, Any] | None = None
    update_mask: list[str] | None = None


class CreatePackageVersionPayload(BaseModel):
    """Payload for creating a package version."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)


class PackageVersionMetaCreate(BaseModel):
    """PackageVersion metadata for creation."""

    name: str = Field(...)
    description: str | None = None


class PackageVersionMetaUpdate(BaseModel):
    """PackageVersion metadata for update."""

    description: str | None = None


def build_create_payload(**kwargs: Any) -> CreatePackageVersionPayload:
    """Build CreatePackageVersionPayload from kwargs (decoupled create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreatePackageVersionPayload, kwargs, attr_name="PackageVersion"
    )
