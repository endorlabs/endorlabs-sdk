"""PackageLicense — thin consumer wrapper over generated V1PackageLicense."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.package_license_service import V1PackageLicense

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class PackageLicense(
    V1PackageLicense, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for PackageLicense (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("PackageLicense")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("PackageLicense")


class CreatePackageLicensePayload(BaseModel):
    """Create payload for PackageLicense."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)


def build_create_payload(**kwargs: Any) -> CreatePackageLicensePayload:
    """Build create payload for PackageLicense."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreatePackageLicensePayload, kwargs, attr_name="PackageLicense"
    )
