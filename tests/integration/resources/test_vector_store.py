"""Integration tests for VectorStore (list/get)."""

from __future__ import annotations

import pytest

import endorlabs
from tests.conftest import TEST_MAX_PAGES, TEST_PAGE_SIZE


@pytest.mark.integration
class TestVectorStore:
    """Validate VectorStore list/get in namespace scope."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace) -> None:
        """Use integration fixtures."""
        self.client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.namespace = namespace

    def test_vector_store_list(self) -> None:
        """LIST vector stores in namespace."""
        result = self.client.VectorStore.list(
            page_size=TEST_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, list)

    def test_vector_store_get(self) -> None:
        """GET first store from LIST when present."""
        items = self.client.VectorStore.list(
            page_size=TEST_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES,
        )
        if not items:
            pytest.skip("No VectorStore rows in this namespace")
        item = items[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.namespace
        )
        got = self.client.VectorStore.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid
