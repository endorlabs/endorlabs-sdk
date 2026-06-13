"""IdentityProvider — thin consumer wrapper over generated V1IdentityProvider."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.identity_provider_service import V1IdentityProvider

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class IdentityProvider(
    V1IdentityProvider, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for IdentityProvider (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("IdentityProvider")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("IdentityProvider")


class CreateIdentityProviderPayload(BaseModel):
    """Create payload for IdentityProvider."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)


def build_create_payload(**kwargs: Any) -> CreateIdentityProviderPayload:
    """Build create payload for IdentityProvider."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateIdentityProviderPayload, kwargs, attr_name="IdentityProvider"
    )
