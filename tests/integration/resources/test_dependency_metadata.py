"""Test cases for DependencyMetadata resource operations.

Tests GET and LIST operations for DependencyMetadata resources.
DependencyMetadata represents dependency relationships between PackageVersions.

Note: The SDK hardcodes the \"oss\" namespace for all DependencyMetadata operations
(list, get, update, create, delete). The tenant/namespace passed to Client or
module functions is ignored. Use endorctl with -n oss to confirm presence/access.
"""

import pytest

from endorlabs.resources import dependency_metadata
from endorlabs.types import ListParameters
from tests.conftest import (
    TEST_MAX_PAGES_TRAVERSE,
    TEST_PAGE_SIZE,
    TEST_TRAVERSE_PAGE_SIZE,
)


@pytest.mark.integration
class TestDependencyMetadata:
    """Test cases for DependencyMetadata resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace, root_namespace) -> None:
        """Fast setup: client and namespaces from conftest (LIST/GET only)."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace

    @pytest.fixture
    def sample_dependency_metadata(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Uses root_namespace + traverse for consistency with other resources.
        """
        results = dependency_metadata.list_dependency_metadata(
            self.client,
            self.root_namespace,
            list_params=ListParameters(
                page_size=TEST_TRAVERSE_PAGE_SIZE,
                traverse=True,
            ),
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    def test_dependency_metadata_list(self) -> None:
        """LIST from tenant root with traverse (registry-based)."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        try:
            result = client.dependency_metadata.list(
                traverse=True,
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        assert isinstance(result, list)

    def test_dependency_metadata_get(self) -> None:
        """GET first item from LIST (root + traverse) (registry-based)."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        try:
            items = client.dependency_metadata.list(
                traverse=True,
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.root_namespace
        )
        got = client.dependency_metadata.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    def test_dependency_metadata_error_handling(self) -> None:
        """Test error handling for invalid UUID."""
        # Test with invalid UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endorlabs.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            dependency_metadata.get_dependency_metadata(
                self.client, self.root_namespace, "invalid-uuid"
            )
        assert exc_info.value.resource_uuid == "invalid-uuid"
        assert exc_info.value.operation == "get"
        assert exc_info.value.status_code == 400

    def test_dependency_metadata_filter_by_project(
        self, sample_dependency_metadata
    ) -> None:
        """Test filtering dependency metadata by project UUID."""
        print("\n=== TESTING FILTER DEPENDENCY METADATA BY PROJECT ===")

        # Get first dependency metadata to extract project UUID
        first_dm = sample_dependency_metadata
        if not first_dm.spec or not first_dm.spec.dependency_data:
            pytest.skip("Dependency metadata has no dependency_data")

        project_uuid = first_dm.spec.dependency_data.project_uuid

        # Filter dependency metadata by project with pagination limits
        list_params = ListParameters(
            filter=f'spec.dependency_data.project_uuid=="{project_uuid}"',
            page_size=TEST_PAGE_SIZE,
        )

        filtered_results = dependency_metadata.list_dependency_metadata(
            self.client,
            self.root_namespace,
            list_params,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )

        assert isinstance(filtered_results, list), (
            "Should return a list of filtered dependency metadata"
        )
        if len(filtered_results) == 0:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

        # Verify all results belong to the project
        for result in filtered_results:
            if result.spec and result.spec.dependency_data:
                assert result.spec.dependency_data.project_uuid == project_uuid, (
                    "All filtered results should belong to the project"
                )

        print(
            f"Found {len(filtered_results)} dependency metadata records "
            f"for project {project_uuid}"
        )
