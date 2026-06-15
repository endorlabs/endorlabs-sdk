"""Unit tests for vector search workflow helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from endorlabs.core.exceptions import ValidationError
from endorlabs.workflows.vector_search.query import (
    list_tenant_vector_stores,
    probe_store_indexed_for_project,
    query_vector_store,
)


def test_list_tenant_vector_stores_name_filter() -> None:
    client = MagicMock()
    client.VectorStore.list.return_value = [
        SimpleNamespace(uuid="1", meta=SimpleNamespace(name="function_summary")),
        SimpleNamespace(uuid="2", meta=SimpleNamespace(name="cwe_knowledge")),
    ]
    out = list_tenant_vector_stores(
        client, namespace="tenant", name_substring="function"
    )
    assert len(out) == 1
    assert out[0].uuid == "1"


def test_query_vector_store_with_metadata_filter() -> None:
    client = MagicMock()
    store = SimpleNamespace(uuid="vs1", namespace="tenant.ns")
    client.VectorStoreQuery.create.return_value = SimpleNamespace(spec=None)
    query_vector_store(
        client,
        store,
        "test query",
        metadata_filter={"repo": "https://github.com/o/r.git"},
    )
    client.VectorStoreQuery.create.assert_called_once()


def test_probe_store_indexed_for_project_query_failure() -> None:
    client = MagicMock()
    store = SimpleNamespace(
        uuid="vs1", namespace="ns", meta=SimpleNamespace(name="function_summary")
    )
    client.VectorStoreQuery.create.side_effect = ValidationError("bad filter")
    result = probe_store_indexed_for_project(client, store, "https://github.com/o/r")
    assert result["indexed"] is False
    assert result["sample_hits"] == 0
    assert result["warnings"]
