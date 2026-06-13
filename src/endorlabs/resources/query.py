"""Query — thin consumer wrapper over generated V1Query."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.query_service import V1Query

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class Query(V1Query, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for Query (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("Query")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("Query")


class CreateQueryPayload(BaseModel):
    """Create payload for Query."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)


def build_create_payload(**kwargs: Any) -> CreateQueryPayload:
    """Build create payload for Query."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(CreateQueryPayload, kwargs, attr_name="Query")
