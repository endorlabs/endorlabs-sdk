"""Test cases for DependencyMetadata resource operations.

Tests GET and LIST operations for DependencyMetadata resources.
DependencyMetadata represents dependency relationships between PackageVersions.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endorlabs.api_client import APIClient
from endorlabs.resources import dependency_metadata
from endorlabs.types import ListParameters


@pytest.mark.integration
class TestDependencyMetadata:
    """Test cases for DependencyMetadata resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self) -> None:
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        import conftest

        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Extract parent namespace from child namespace if needed
        parts = self.namespace.split(".")
        self.parent_namespace = parts[0] if len(parts) > 1 else self.namespace

    @pytest.fixture
    def sample_dependency_metadata(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Only fetches 1 item without traverse for fast setup. Tests that need
        sample data should request this fixture explicitly.
        """
        # Fetch 1 item without traverse (fast)
        results = dependency_metadata.list_dependency_metadata(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=1),
            max_pages=1,
        )
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    def test_dependency_metadata_get_list(self) -> None:
        """Test GET dependency-metadata operation."""
        print("\n=== TESTING GET DEPENDENCY METADATA ===")

        # Test list_dependency_metadata with pagination limits
        import conftest

        dependency_metadata_list = dependency_metadata.list_dependency_metadata(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(dependency_metadata_list, list), (
            "Should return a list of dependency metadata"
        )
        if len(dependency_metadata_list) == 0:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

        print(f"Found {len(dependency_metadata_list)} dependency metadata records")

        # Verify structure
        for dm in dependency_metadata_list[:5]:  # Show first 5
            assert hasattr(dm, "uuid")
            assert hasattr(dm, "meta")
            assert hasattr(dm, "spec")
            assert hasattr(dm, "tenant_meta")

            # Verify meta fields
            assert hasattr(dm.meta, "name")
            assert hasattr(dm.meta, "create_time")

            # Verify spec fields
            if dm.spec:
                assert hasattr(dm.spec, "dependency_data")
                assert hasattr(dm.spec, "importer_data")

                if dm.spec.dependency_data:
                    print(
                        f"DependencyMetadata {dm.uuid}: "
                        f"{dm.spec.dependency_data.package_name}"
                    )
                    if dm.spec.dependency_data.ecosystem:
                        print(f"  Ecosystem: {dm.spec.dependency_data.ecosystem}")

    def test_dependency_metadata_get_by_uuid(self, sample_dependency_metadata) -> None:
        """Test GET dependency-metadata by UUID operation."""
        print("\n=== TESTING GET DEPENDENCY METADATA BY UUID ===")

        test_dm = sample_dependency_metadata
        # Use the dependency metadata's actual namespace
        dm_namespace = (
            test_dm.tenant_meta.namespace
            if test_dm.tenant_meta
            else self.parent_namespace
        )
        retrieved_dm = dependency_metadata.get_dependency_metadata(
            self.client, dm_namespace, test_dm.uuid
        )

        assert retrieved_dm is not None, (
            "Should successfully retrieve dependency metadata by UUID"
        )
        assert retrieved_dm.uuid == test_dm.uuid, (
            "Retrieved dependency metadata should match original"
        )
        if retrieved_dm.meta and test_dm.meta:
            assert retrieved_dm.meta.name == test_dm.meta.name, (
                "Dependency metadata name should match"
            )

        print(f"Successfully retrieved dependency metadata: {retrieved_dm.uuid}")
        if retrieved_dm.meta:
            print(f"Dependency metadata name: {retrieved_dm.meta.name}")
        if retrieved_dm.spec and retrieved_dm.spec.dependency_data:
            print(f"Package name: {retrieved_dm.spec.dependency_data.package_name}")
            if retrieved_dm.spec.dependency_data.ecosystem:
                print(f"Ecosystem: {retrieved_dm.spec.dependency_data.ecosystem}")

    def test_dependency_metadata_pagination(self) -> None:
        """Test pagination capabilities."""
        # Test with page size and max_pages limit
        import conftest

        paginated_results = dependency_metadata.list_dependency_metadata(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=5),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(paginated_results, list)
        if len(paginated_results) == 0:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

    def test_dependency_metadata_error_handling(self) -> None:
        """Test error handling for invalid UUID."""
        # Test with invalid UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endorlabs.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            dependency_metadata.get_dependency_metadata(
                self.client, self.parent_namespace, "invalid-uuid"
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
        import conftest

        list_params = ListParameters(
            filter=f'spec.dependency_data.project_uuid=="{project_uuid}"',
            page_size=conftest.TEST_PAGE_SIZE,
        )

        filtered_results = dependency_metadata.list_dependency_metadata(
            self.client,
            self.parent_namespace,
            list_params,
            max_pages=conftest.TEST_MAX_PAGES,
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

    def test_client_recommended_ux_list_dependency_metadata(self) -> None:
        """Recommended UX: Client(tenant=...); client.dependency_metadata.list()."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.namespace,
            max_retries=2,
            backoff_factor=0.1,
            auth_method="api-key",
        )
        try:
            items = client.dependency_metadata.list(max_pages=1)
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        assert isinstance(items, list)
