"""LinterResult — thin consumer wrapper over generated V1LinterResult."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.linter_result_service import V1LinterResult

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin, LinterResultSpec

__all__ = [
    "CreateLinterResultPayload",
    "LinterResult",
    "LinterResultSpec",
    "build_create_payload",
]


class LinterResult(V1LinterResult, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for LinterResult (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("LinterResult")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("LinterResult")

    spec: LinterResultSpec | None = None  # pyright: ignore[reportIncompatibleVariableOverride]


class CreateLinterResultPayload(BaseModel):
    """Create payload for LinterResult."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)


def build_create_payload(**kwargs: Any) -> CreateLinterResultPayload:
    """Build create payload for LinterResult."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateLinterResultPayload, kwargs, attr_name="LinterResult"
    )
