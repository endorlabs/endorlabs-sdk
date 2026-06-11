"""VectorStore resource facade model.

Read-oriented facade for vector store inventory resources.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field

from .base import BaseResource, BaseSpec

if TYPE_CHECKING:
    from ..client_surface import Client
    from .vector_store_query import VectorStoreQuery


class VectorStoreSpec(BaseSpec):
    """Vector store specification.

    The API schema for this service is evolving; keep this permissive so list/get
    can succeed without strict field coupling.
    """

    dimensions: int | None = Field(None, description="Embedding dimensions")
    embedding_model: str | None = Field(None, description="Embedding model")
    embedding_provider: str | None = Field(None, description="Embedding provider")
    uniqueness_fields: str | None = Field(
        None, description="Metadata keys used for uniqueness"
    )


class VectorStore(BaseResource):
    """Vector store resource.

    Used for facade list/get operations.
    """

    spec: VectorStoreSpec | dict[str, Any] | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Vector store specification"
    )

    def query(self, query: str, *, client: Client) -> VectorStoreQuery:
        """Run a natural-language query against this vector store.

        Delegates to ``client.VectorStoreQuery.create`` using this store's
        ``uuid`` and ``tenant_meta.namespace``. Requires a hydrated store from
        list/get (``namespace`` must be present).

        Args:
            query: Natural-language query (e.g. functions that sanitize input).
            client: ``endorlabs.Client`` instance.

        Returns:
            ``VectorStoreQuery`` response from the API.
        """
        ns = self.namespace
        if ns is None:
            raise ValueError(
                "VectorStore.query requires tenant_meta.namespace on the store; "
                "use a store from list/get, or call "
                "client.VectorStoreQuery.create(vector_store_uuid=..., query=..., "
                "namespace=...) directly."
            )
        return client.VectorStoreQuery.create(
            vector_store_uuid=self.uuid,
            query=query,
            namespace=ns,
        )
