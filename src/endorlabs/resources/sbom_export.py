"""SBOMExport — thin consumer wrapper over generated V1ExportedSBOM."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.s_b_o_m_export_service import V1ExportedSBOM

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class SBOMExport(V1ExportedSBOM, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for SBOM export create responses."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("SBOMExport")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("SBOMExport")


class CreateSBOMExportPayload(BaseModel):
    """Create payload for SBOMExport."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)
    tenant_meta: dict[str, Any] | BaseModel | None = None


def build_create_payload(**kwargs: Any) -> CreateSBOMExportPayload:
    """Build create payload for SBOMExport."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateSBOMExportPayload, kwargs, attr_name="SBOMExport"
    )
