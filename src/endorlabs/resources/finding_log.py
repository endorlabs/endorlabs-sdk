"""FindingLog — thin consumer wrapper over generated V1FindingLog."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.finding_log_service import (
    V1FindingLog,
)
from endorlabs.generated.models.finding_log_service import (
    V1FindingLogSpec as _V1FindingLogSpec,
)

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import (
    ConsumerContext,
    ConsumerResourceWireMixin,
    partial_spec_model,
)

FindingLogSpec = partial_spec_model(_V1FindingLogSpec, name="FindingLogSpec")


class FindingLog(V1FindingLog, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for FindingLog (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("FindingLog")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("FindingLog")

    spec: FindingLogSpec | None = None  # pyright: ignore[reportIncompatibleVariableOverride]
    context: ConsumerContext | None = None  # pyright: ignore[reportIncompatibleVariableOverride]


class CreateFindingLogPayload(BaseModel):
    """Create payload for FindingLog."""

    meta: dict[str, Any] | BaseModel = Field(...)
    context: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)


def build_create_payload(**kwargs: Any) -> CreateFindingLogPayload:
    """Build create payload for FindingLog."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateFindingLogPayload, kwargs, attr_name="FindingLog"
    )
