"""Scoped vector store listing and query helpers for agent workflows."""

from __future__ import annotations

from typing import Any

from endorlabs.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ServerError,
    ValidationError,
)


def list_tenant_vector_stores(
    client: Any,
    *,
    namespace: str,
    name_substring: str = "",
    max_pages: int = 1,
) -> list[Any]:
    """List vector stores in *namespace*, optionally filtered by name substring."""
    stores = client.VectorStore.list(namespace=namespace, max_pages=max_pages)
    if not name_substring:
        return stores
    needle = name_substring.lower()
    return [
        vs
        for vs in stores
        if vs.meta and vs.meta.name and needle in vs.meta.name.lower()
    ]


def query_vector_store(
    client: Any,
    store: Any,
    query: str,
    *,
    metadata_filter: dict[str, Any] | None = None,
) -> Any:
    """Run a natural-language query, optionally scoped by metadata_filter."""
    if metadata_filter:
        return client.VectorStoreQuery.create(
            vector_store_uuid=store.uuid,
            query=query,
            namespace=store.namespace,
            metadata_filter=metadata_filter,
        )
    return store.query(query, client=client)


def probe_store_indexed_for_project(
    client: Any,
    store: Any,
    project_meta_name: str,
    *,
    probe_query: str = "function",
) -> dict[str, Any]:
    """Check whether *store* returns hits scoped to *project_meta_name* metadata."""
    warnings: list[str] = []
    metadata_filter = {"repo": project_meta_name}
    try:
        result = query_vector_store(
            client,
            store,
            probe_query,
            metadata_filter=metadata_filter,
        )
    except (PermissionDeniedError, ValidationError, NotFoundError, ServerError) as exc:
        return {
            "store_uuid": store.uuid,
            "store_name": store.meta.name if store.meta else store.uuid,
            "indexed": False,
            "sample_hits": 0,
            "warnings": [f"query_failed: {exc}"],
        }

    hits = 0
    spec = getattr(result, "spec", None)
    if spec is not None:
        documents = getattr(spec, "documents", None) or []
        hits = len(documents)
    if hits == 0:
        warnings.append(
            f"No documents matched metadata_filter repo={project_meta_name!r}; "
            "project may not be indexed in this store."
        )

    return {
        "store_uuid": store.uuid,
        "store_name": store.meta.name if store.meta else store.uuid,
        "indexed": hits > 0,
        "sample_hits": hits,
        "warnings": warnings,
    }
