"""ImportedSBOM — thin consumer wrapper over generated V1ImportedSBOM."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.s_b_o_m_import_service import V1ImportedSBOM

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class ImportedSBOM(V1ImportedSBOM, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for ImportedSBOM (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("ImportedSBOM")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("ImportedSBOM")

    def linked_project_uuid(self) -> str | None:
        """Return ``meta.parent_uuid`` when the import is linked to a Project."""
        meta = getattr(self, "meta", None)
        parent = getattr(meta, "parent_uuid", None) if meta is not None else None
        if parent is None:
            return None
        value = getattr(parent, "value", parent)
        return str(value) if value else None


class CreateImportedSBOMPayload(BaseModel):
    """Create payload for ImportedSBOM."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)
    context: dict[str, Any] | BaseModel | None = None
    tenant_meta: dict[str, Any] | BaseModel | None = None


def build_create_payload(**kwargs: Any) -> CreateImportedSBOMPayload:
    """Build create payload for ImportedSBOM."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateImportedSBOMPayload, kwargs, attr_name="ImportedSBOM"
    )
