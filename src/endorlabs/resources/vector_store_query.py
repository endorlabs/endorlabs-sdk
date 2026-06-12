"""VectorStoreQuery resource module for Endor Labs API.

This resource maps to ``POST /v1/namespaces/{namespace}/queries/vector-stores``
(tenant namespace; matches ``VectorStoreQueryService_CreateVectorStoreQuery``) and
supports natural-language queries against a vector store identified by UUID
(typically ``function_summary`` or ``file_summary`` stores from
``client.VectorStore``).
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from ..generated.create_convenience import (
    VECTOR_STORE_QUERY_META_FIELDS,
    VECTOR_STORE_QUERY_SPEC_FIELDS,
)
from ..utils.create_payload import promote_create_kwargs
from ..utils.logging_config import get_resource_logger
from .base import BaseMeta, BaseResource, BaseSpec

logger = get_resource_logger(__name__)


class VectorStoreQuerySpec(BaseSpec):
    """VectorStoreQuery request specification."""

    vector_store_uuid: str | None = Field(
        None,
        description=(
            "UUID of the VectorStore to query (e.g. function_summary or file_summary)."
        ),
    )
    query: str | None = Field(
        None,
        description="Natural-language query string.",
    )
    metadata_filter: dict[str, Any] | None = Field(
        None,
        description="Optional metadata filter to scope similarity search.",
    )

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow")


class VectorStoreQuery(BaseResource):
    """VectorStoreQuery resource model returned by the query endpoint."""

    uuid: str | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None,
        description="UUID (often null for this request/response style API).",
    )
    meta: BaseMeta | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None,
        description="Metadata (may be null in responses).",
    )
    spec: VectorStoreQuerySpec | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None,
        description="Query request specification.",
    )
    response: dict[str, Any] | None = Field(
        None,
        description="Single query response payload.",
    )
    responses: dict[str, Any] | None = Field(
        None,
        description="Batch query response map.",
    )

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")


class VectorStoreQueryMetaCreate(BaseModel):
    """Metadata payload for vector store query requests."""

    name: str = Field(..., description="Human-readable query name.")


class CreateVectorStoreQueryPayload(BaseModel):
    """Payload for creating a vector store query request."""

    meta: VectorStoreQueryMetaCreate = Field(..., description="Query metadata.")
    spec: VectorStoreQuerySpec = Field(..., description="Query specification.")


def build_create_payload(**kwargs: Any) -> CreateVectorStoreQueryPayload:
    """Build CreateVectorStoreQueryPayload from kwargs.

    Supports either explicit payload style (``meta=...``, ``spec=...``) or
    convenience kwargs used by ``ResourceRuntimeFacade.create(...)``.
    """
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
