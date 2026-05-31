"""Test cases for DependencyMetadata resource operations.

DependencyMetadata is tenant-scoped: list/get use the customer namespace path.
``spec.dependency_data.namespace`` may still be ``oss`` for catalog-backed packages.
"""

from __future__ import annotations

import pytest

import endorlabs
from endorlabs.core.exceptions import ServerError
from endorlabs.core.types import ListParameters
from tests.conftest import (
    TEST_MAX_PAGES_TRAVERSE,
    TEST_PAGE_SIZE,
    TEST_TRAVERSE_PAGE_SIZE,
)


@pytest.mark.integration
class TestDependencyMetadata:
    """Integration tests for DependencyMetadata (tenant namespace)."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace, root_namespace) -> None:
        """Fast setup: client and namespaces from conftest."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.endor_root_client = endorlabs.Client(
            tenant=root_namespace, api_client=api_client
        )

    @pytest.fixture
    def sample_dependency_metadata(self):
        """Fetch one row from tenant root with traverse."""
        results = self.endor_root_client.DependencyMetadata.list(
            traverse=True,
            page_size=TEST_TRAVERSE_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]

    def test_dependency_metadata_list_uses_tenant_namespace(self) -> None:
        """LIST with traverse returns rows under the tenant namespace path."""
        try:
            result = self.endor_root_client.DependencyMetadata.list(
                traverse=True,
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        assert isinstance(result, list)
        if not result:
            pytest.skip("No dependency metadata in scope")
        first = result[0]
        if first.tenant_meta and first.tenant_meta.namespace:
            assert self.root_namespace in str(first.tenant_meta.namespace)

    def test_dependency_metadata_get(self) -> None:
        """GET by UUID in tenant namespace."""
        try:
            items = self.endor_root_client.DependencyMetadata.list(
                traverse=True,
                max_pages=1,
                page_size=TEST_PAGE_SIZE,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not items:
            pytest.skip("No dependency metadata in scope")
        item = items[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and item.tenant_meta.namespace
            else self.root_namespace
        )
        got = self.endor_root_client.DependencyMetadata.get(item.uuid, namespace=ns)
        assert got.uuid == item.uuid

    def test_dependency_metadata_error_handling(self) -> None:
        """Invalid UUID raises typed error."""
        from endorlabs.core.exceptions import EndorAPIError

        with pytest.raises(EndorAPIError):
            self.endor_root_client.DependencyMetadata.get(
                "invalid-uuid", namespace=self.root_namespace
            )

    def test_dependency_metadata_filter_by_project(
        self, sample_dependency_metadata
    ) -> None:
        """Filter by importer project UUID in the row's owning namespace."""
        first_dm = sample_dependency_metadata
        project_uuid = None
        if first_dm.spec and first_dm.spec.importer_data:
            project_uuid = first_dm.spec.importer_data.project_uuid
        if not project_uuid:
            pytest.skip("Sample row has no importer project_uuid")

        project_ns = (
            first_dm.tenant_meta.namespace
            if first_dm.tenant_meta and first_dm.tenant_meta.namespace
            else self.root_namespace
        )

        filtered_results = self.endor_root_client.DependencyMetadata.list(
            namespace=project_ns,
            traverse=False,
            filter=f'spec.importer_data.project_uuid=="{project_uuid}"',
            page_size=TEST_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(filtered_results, list)
        assert len(filtered_results) >= 1
        for dm in filtered_results:
            if dm.spec and dm.spec.importer_data:
                assert dm.spec.importer_data.project_uuid == project_uuid

    def test_dependency_metadata_count_vs_list_bounded(self) -> None:
        """Traverse count is consistent with a bounded materialized list."""
        ops = self.endor_root_client.DependencyMetadata._ops
        try:
            total = ops.count(
                self.root_namespace,
                ListParameters(traverse=True, page_size=TEST_TRAVERSE_PAGE_SIZE),
            )
        except ServerError:
            pytest.skip("Backend count failed")
        if total == 0:
            pytest.skip("No dependency metadata to compare")

        listed = self.endor_root_client.DependencyMetadata.list(
            traverse=True,
            max_pages=1,
            page_size=TEST_PAGE_SIZE,
        )
        assert len(listed) <= total
