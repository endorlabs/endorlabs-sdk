"""VectorStoreQuery — thin consumer wrapper with create payload helpers."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from endorlabs.generated.models.vector import V1VectorStoreQuery

from ..generated.create_convenience import (
    VECTOR_STORE_QUERY_META_FIELDS,
    VECTOR_STORE_QUERY_SPEC_FIELDS,
)
from ..utils.create_payload import promote_create_kwargs
from .base import BaseSpec
from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class VectorStoreQuerySpec(BaseSpec):
    """VectorStoreQuery request specification."""

    vector_store_uuid: str | None = Field(None, description="UUID of the VectorStore.")
    query: str | None = Field(None, description="Natural-language query string.")
    metadata_filter: dict[str, Any] | None = Field(
        None, description="Optional metadata filter."
    )

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow")


class VectorStoreQuery(
    V1VectorStoreQuery, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for VectorStoreQuery (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("VectorStoreQuery")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("VectorStoreQuery")


class VectorStoreQueryMetaCreate(BaseModel):
    """Metadata payload for vector store query requests."""

    name: str = Field(..., description="Human-readable query name.")


class CreateVectorStoreQueryPayload(BaseModel):
    """Payload for creating a vector store query request."""

    meta: VectorStoreQueryMetaCreate = Field(..., description="Query metadata.")
    spec: VectorStoreQuerySpec = Field(..., description="Query specification.")


def build_create_payload(**kwargs: Any) -> CreateVectorStoreQueryPayload:
    """Build CreateVectorStoreQueryPayload from kwargs."""
    meta_aliases = {
        name: "name" for name in VECTOR_STORE_QUERY_META_FIELDS if name == "name"
    }
    payload_kwargs = promote_create_kwargs(
        dict(kwargs),
        spec_fields=VECTOR_STORE_QUERY_SPEC_FIELDS,
        meta_name_default="vector-store-query",
        meta_flat_aliases=meta_aliases,
        resource_label="VectorStoreQuery",
    )
    return CreateVectorStoreQueryPayload(**payload_kwargs)
