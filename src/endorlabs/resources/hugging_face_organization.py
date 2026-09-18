"""HuggingFaceOrganization — thin consumer wrapper over generated model."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.hugging_face_organization_service import (
    V1HuggingFaceOrganization,
)

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin

__all__ = [
    "CreateHuggingFaceOrganizationPayload",
    "HuggingFaceOrganization",
    "build_create_payload",
]


class HuggingFaceOrganization(
    V1HuggingFaceOrganization, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for HuggingFaceOrganization (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str] | None] = (
        mutable_fields_for("HuggingFaceOrganization") or None
    )
    _IMMUTABLE_FIELDS: ClassVar[list[str] | None] = (
        immutable_fields_for("HuggingFaceOrganization") or None
    )


class CreateHuggingFaceOrganizationPayload(BaseModel):
    """Create payload for HuggingFaceOrganization (API create is x-internal)."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)


def build_create_payload(**kwargs: Any) -> CreateHuggingFaceOrganizationPayload:
    """Build create payload for HuggingFaceOrganization."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateHuggingFaceOrganizationPayload,
        kwargs,
        attr_name="HuggingFaceOrganization",
    )
