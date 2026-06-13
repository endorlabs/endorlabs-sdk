"""Metric — thin consumer wrapper over generated Endorv1Metric."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.metric_service import Endorv1Metric

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class Metric(Endorv1Metric, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for Metric (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("Metric")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("Metric")


class CreateMetricPayload(BaseModel):
    """Create payload for Metric."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)


def build_create_payload(**kwargs: Any) -> CreateMetricPayload:
    """Build create payload for Metric."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(CreateMetricPayload, kwargs, attr_name="Metric")
