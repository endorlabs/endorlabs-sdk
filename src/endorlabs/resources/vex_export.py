"""VEXExport — thin consumer wrapper over generated V1ExportedVEX."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.v_e_x_export_service import V1ExportedVEX

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class VEXExport(V1ExportedVEX, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for VEX export create responses."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("VEXExport")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("VEXExport")


class CreateVEXExportPayload(BaseModel):
    """Create payload for VEXExport."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)
    tenant_meta: dict[str, Any] | BaseModel | None = None


def build_create_payload(**kwargs: Any) -> CreateVEXExportPayload:
    """Build create payload for VEXExport."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateVEXExportPayload, kwargs, attr_name="VEXExport"
    )
