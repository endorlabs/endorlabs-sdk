"""VectorStore — thin consumer wrapper over generated V1VectorStore."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from endorlabs.generated.models.vector_store_service import V1VectorStore

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin, VectorStoreSpec

if TYPE_CHECKING:
    from ..client_surface import Client
    from .vector_store_query import VectorStoreQuery


class VectorStore(V1VectorStore, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for VectorStore (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("VectorStore")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("VectorStore")

    spec: VectorStoreSpec | None = None  # pyright: ignore[reportIncompatibleVariableOverride]

    def query(self, query: str, *, client: Client) -> VectorStoreQuery:
        """Run a natural-language query against this vector store."""
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
