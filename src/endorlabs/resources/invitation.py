"""Invitation — thin consumer wrapper over generated V1Invitation."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.invitation_service import V1Invitation

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class Invitation(V1Invitation, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for Invitation (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("Invitation")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("Invitation")


class CreateInvitationPayload(BaseModel):
    """Create payload for Invitation."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)


def build_create_payload(**kwargs: Any) -> CreateInvitationPayload:
    """Build create payload for Invitation."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateInvitationPayload, kwargs, attr_name="Invitation"
    )
