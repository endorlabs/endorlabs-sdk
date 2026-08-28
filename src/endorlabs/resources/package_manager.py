"""PackageManager — thin consumer wrapper over generated V1PackageManager."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.package_manager_service import V1PackageManager

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class PackageManager(
    V1PackageManager, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for PackageManager (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str] | None] = (
        mutable_fields_for("PackageManager") or None
    )
    # Empty registry list must not pin []; fall through to mixin defaults.
    _IMMUTABLE_FIELDS: ClassVar[list[str] | None] = (
        immutable_fields_for("PackageManager") or None
    )


class CreatePackageManagerPayload(BaseModel):
    """Create payload for PackageManager."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)
    propagate: bool | None = None


def build_create_payload(**kwargs: Any) -> CreatePackageManagerPayload:
    """Build create payload for PackageManager."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreatePackageManagerPayload, kwargs, attr_name="PackageManager"
    )
