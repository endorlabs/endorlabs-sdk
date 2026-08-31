"""SystemConfig — thin consumer wrapper over generated V1SystemConfig."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.system_config_service import V1SystemConfig

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class SystemConfig(V1SystemConfig, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for SystemConfig (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str] | None] = (
        mutable_fields_for("SystemConfig") or None
    )
    # Empty registry list must not pin []; fall through to mixin defaults.
    _IMMUTABLE_FIELDS: ClassVar[list[str] | None] = (
        immutable_fields_for("SystemConfig") or None
    )


class CreateSystemConfigPayload(BaseModel):
    """Create payload for SystemConfig."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)
    propagate: bool | None = None


def build_create_payload(**kwargs: Any) -> CreateSystemConfigPayload:
    """Build create payload for SystemConfig."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateSystemConfigPayload, kwargs, attr_name="SystemConfig"
    )
