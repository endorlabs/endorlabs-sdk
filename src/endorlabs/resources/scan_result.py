"""ScanResult — thin consumer wrapper over generated V1ScanResult."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.scan_result_service import V1ScanResult

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerContext, ConsumerResourceWireMixin


class ScanResult(V1ScanResult, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for ScanResult (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("ScanResult")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("ScanResult")

    context: ConsumerContext | None = None  # pyright: ignore[reportIncompatibleVariableOverride]


class CreateScanResultPayload(BaseModel):
    """Create payload for ScanResult."""

    meta: dict[str, Any] | BaseModel = Field(...)
    context: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)


def build_create_payload(**kwargs: Any) -> CreateScanResultPayload:
    """Build create payload for ScanResult."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateScanResultPayload, kwargs, attr_name="ScanResult"
    )
