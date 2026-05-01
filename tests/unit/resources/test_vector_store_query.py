"""Unit tests for VectorStoreQuery resource models and create payload builder."""

from __future__ import annotations

import pytest

from endorlabs.models.base import BaseMeta, TenantMeta
from endorlabs.resources.vector_store import VectorStore, VectorStoreSpec
from endorlabs.resources.vector_store_query import (
    CreateVectorStoreQueryPayload,
    VectorStoreQueryMetaCreate,
    VectorStoreQuerySpec,
    build_create_payload,
)


def test_build_create_payload_convenience_kwargs() -> None:
    """Builder merges name, vector_store_uuid, and query into meta/spec."""
    payload = build_create_payload(
        name="my-query",
        vector_store_uuid="store-uuid-1",
        query="functions that sanitize input",
    )
    assert isinstance(payload, CreateVectorStoreQueryPayload)
    assert payload.meta.name == "my-query"
    assert payload.spec.vector_store_uuid == "store-uuid-1"
    assert payload.spec.query == "functions that sanitize input"


def test_build_create_payload_default_name() -> None:
    """Default meta.name when omitted."""
    payload = build_create_payload(
        vector_store_uuid="u1",
        query="network entrypoint",
    )
    assert payload.meta.name == "vector-store-query"


def test_build_create_payload_explicit_meta_spec() -> None:
    """Explicit meta= and spec= bypass convenience assembly."""
    payload = build_create_payload(
        meta=VectorStoreQueryMetaCreate(name="explicit"),
        spec=VectorStoreQuerySpec(
            vector_store_uuid="vs-2",
            query="files related to auth",
        ),
    )
    assert payload.meta.name == "explicit"
    assert payload.spec.vector_store_uuid == "vs-2"
    assert payload.spec.query == "files related to auth"


def test_create_payload_model_dump() -> None:
    """Payload serializes for API client."""
    payload = CreateVectorStoreQueryPayload(
        meta=VectorStoreQueryMetaCreate(name="n"),
        spec=VectorStoreQuerySpec(vector_store_uuid="a", query="b"),
    )
    data = payload.model_dump()
    assert data["meta"]["name"] == "n"
    assert data["spec"]["vector_store_uuid"] == "a"
    assert data["spec"]["query"] == "b"


def test_vector_store_query_raises_when_namespace_missing() -> None:
    """query() requires tenant_meta.namespace."""
    from unittest.mock import Mock

    from endorlabs.client_surface import Client

    vs = VectorStore(
        uuid="vs-uuid",
        meta=BaseMeta(name="function_summary"),
        spec=VectorStoreSpec(),
        tenant_meta=None,
    )
    client = Mock(spec=Client)
    with pytest.raises(ValueError, match=r"tenant_meta\.namespace"):
        vs.query("anything", client=client)


def test_vector_store_query_delegates_to_client() -> None:
    """query() forwards uuid, query, and namespace to VectorStoreQuery.create."""
    from unittest.mock import Mock

    from endorlabs.client_surface import Client

    vs = VectorStore(
        uuid="store-abc",
        meta=BaseMeta(name="function_summary"),
        spec=VectorStoreSpec(),
        tenant_meta=TenantMeta(namespace="tenant.team"),
    )
    mock_result = Mock()
    client = Mock(spec=Client)
    client.VectorStoreQuery = Mock()
    client.VectorStoreQuery.create = Mock(return_value=mock_result)

    out = vs.query("find sanitizers", client=client)

    assert out is mock_result
    client.VectorStoreQuery.create.assert_called_once_with(
        vector_store_uuid="store-abc",
        query="find sanitizers",
        namespace="tenant.team",
    )
