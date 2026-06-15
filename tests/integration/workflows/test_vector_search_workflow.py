"""Integration tests for vector search workflow helpers."""

from __future__ import annotations

import pytest

import endorlabs
from endorlabs.core.exceptions import ServerError
from endorlabs.workflows.vector_search.query import (
    list_tenant_vector_stores,
    probe_store_indexed_for_project,
)


@pytest.mark.integration
class TestVectorSearchWorkflow:
    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace) -> None:
        self.client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.namespace = namespace

    def test_list_tenant_vector_stores(self) -> None:
        try:
            stores = list_tenant_vector_stores(self.client, namespace=self.namespace)
        except ServerError:
            pytest.skip("VectorStore list not available")
        if not stores:
            pytest.skip("No vector stores in tenant")
        assert stores[0].uuid

    def test_probe_function_summary_for_endorlabs_sdk(self) -> None:
        try:
            stores = list_tenant_vector_stores(
                self.client,
                namespace=self.namespace,
                name_substring="function_summary",
            )
        except ServerError:
            pytest.skip("VectorStore list not available")
        if not stores:
            pytest.skip("No function_summary store")
        try:
            proj = self.client.Project.search_by_name(
                "endorlabs-sdk",
                namespace=self.namespace,
                traverse=True,
                max_pages=1,
            )
        except ServerError:
            pytest.skip("Project search unavailable")
        if not proj:
            pytest.skip("endorlabs-sdk project not found")
        project_name = proj[0].meta.name if proj[0].meta else proj[0].uuid
        result = probe_store_indexed_for_project(self.client, stores[0], project_name)
        assert "indexed" in result
        assert "sample_hits" in result
