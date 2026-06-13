"""SavedQuery — thin consumer wrapper over generated V1SavedQuery."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.saved_query_service import V1SavedQuery

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class SavedQuery(V1SavedQuery, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for SavedQuery (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("SavedQuery")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("SavedQuery")


class CreateSavedQueryPayload(BaseModel):
    """Create payload for SavedQuery."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)


def build_create_payload(**kwargs: Any) -> CreateSavedQueryPayload:
    """Build create payload for SavedQuery."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateSavedQueryPayload, kwargs, attr_name="SavedQuery"
    )
