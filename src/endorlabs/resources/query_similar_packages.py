"""Thin consumer wrapper for generated V1QuerySimilarPackages."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.query_similar_packages_service import (
    V1QuerySimilarPackages,
)

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class QuerySimilarPackages(
    V1QuerySimilarPackages, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for QuerySimilarPackages (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("QuerySimilarPackages")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for(
        "QuerySimilarPackages"
    )


class CreateQuerySimilarPackagesPayload(BaseModel):
    """Create payload for QuerySimilarPackages."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)


def build_create_payload(**kwargs: Any) -> CreateQuerySimilarPackagesPayload:
    """Build create payload for QuerySimilarPackages."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateQuerySimilarPackagesPayload, kwargs, attr_name="QuerySimilarPackages"
    )
