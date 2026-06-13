"""Installation — thin consumer wrapper over generated V1Installation."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.installation_service import V1Installation

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin, InstallationSpec

__all__ = [
    "CreateInstallationPayload",
    "Installation",
    "InstallationSpec",
    "build_create_payload",
]


class Installation(V1Installation, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for Installation (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("Installation")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("Installation")

    spec: InstallationSpec | None = None  # pyright: ignore[reportIncompatibleVariableOverride]


class CreateInstallationPayload(BaseModel):
    """Create payload for Installation."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)


def build_create_payload(**kwargs: Any) -> CreateInstallationPayload:
    """Build create payload for Installation."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateInstallationPayload, kwargs, attr_name="Installation"
    )
