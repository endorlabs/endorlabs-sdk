"""Integration tests for VectorStoreQuery (natural-language vector search)."""

from __future__ import annotations

import pytest

import endorlabs
from endorlabs.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ServerError,
    ValidationError,
)


@pytest.mark.integration
class TestVectorStoreQuery:
    """Validate VectorStoreQuery create and VectorStore.query ergonomic."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace) -> None:
        """Use integration fixtures."""
        self.client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.namespace = namespace

    @pytest.fixture
    def function_summary_store(self):
        """Resolve the function_summary vector store when present in this tenant."""
        try:
            matches = self.client.VectorStore.search_by_name("function_summary")
        except ServerError:
            pytest.skip("No function_summary VectorStore in this tenant")
        if not matches:
            pytest.skip("No function_summary VectorStore in this tenant")
        vs = matches[0]
        assert vs.uuid
        assert vs.meta is not None
        return vs

    @pytest.mark.writes
    def test_vector_store_query_natural_language(self, function_summary_store) -> None:
        """POST vector store query via VectorStore.query helper."""
        vs = function_summary_store
        try:
            result = vs.query(
                "functions that sanitize a command injection",
                client=self.client,
            )
        except (
            PermissionDeniedError,
            ValidationError,
            NotFoundError,
            ServerError,
        ) as exc:
            pytest.skip(f"Vector store query not available in this environment: {exc}")

        assert result is not None
        assert result.meta is not None

    @pytest.mark.writes
    def test_vector_store_query_metadata_filter_round_trip(
        self, function_summary_store
    ) -> None:
        """Flat metadata_filter on create is accepted by the API."""
        vs = function_summary_store
        filter_value = {"repo": "https://github.com/endorlabs/endorlabs-sdk.git"}
        try:
            result = self.client.VectorStoreQuery.create(
                name="sdk-metadata-filter-test",
                vector_store_uuid=vs.uuid,
                query="entrypoint functions",
                metadata_filter=filter_value,
                namespace=self.namespace,
            )
        except (
            PermissionDeniedError,
            ValidationError,
            NotFoundError,
            ServerError,
        ) as exc:
            pytest.skip(f"Vector store query create not available: {exc}")

        assert result is not None
        metadata_filter = getattr(result.spec, "metadata_filter", None)
        if metadata_filter is not None:
            assert metadata_filter == filter_value
