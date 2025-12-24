"""
Test cases for DependencyMetadata resource operations.

Tests GET and LIST operations for DependencyMetadata resources.
DependencyMetadata represents dependency relationships between PackageVersions.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import dependency_metadata
from endor_cockpit.types import ListParameters


@pytest.mark.integration
class TestDependencyMetadata:
    """Test cases for DependencyMetadata resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = APIClient()
        self.namespace = os.getenv("ENDOR_NAMESPACE", "")

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Get test data with pagination limits
        import conftest

        # Extract parent namespace from child namespace if needed
        parts = self.namespace.split(".")
        self.parent_namespace = parts[0] if len(parts) > 1 else self.namespace

        self.dependency_metadata_list = dependency_metadata.list_dependency_metadata(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
        )
        if not self.dependency_metadata_list:
            pytest.skip("No dependency metadata available for testing")

    def test_dependency_metadata_get_list(self):
        """Test GET dependency-metadata operation."""
        print("\n=== TESTING GET DEPENDENCY METADATA ===")

        # Test list_dependency_metadata
        dependency_metadata_list = dependency_metadata.list_dependency_metadata(
            self.client, self.parent_namespace
        )
        assert isinstance(dependency_metadata_list, list), (
            "Should return a list of dependency metadata"
        )
        assert len(dependency_metadata_list) > 0, (
            "Should have at least one dependency metadata"
        )

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

    def test_dependency_metadata_get_by_uuid(self):
        """Test GET dependency-metadata by UUID operation."""
        print("\n=== TESTING GET DEPENDENCY METADATA BY UUID ===")

        test_dm = self.dependency_metadata_list[0]
        retrieved_dm = dependency_metadata.get_dependency_metadata(
            self.client, self.parent_namespace, test_dm.uuid
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
            print(
                f"Package name: {retrieved_dm.spec.dependency_data.package_name}"
            )
            if retrieved_dm.spec.dependency_data.ecosystem:
                print(
                    f"Ecosystem: {retrieved_dm.spec.dependency_data.ecosystem}"
                )

    def test_dependency_metadata_field_validation(self):
        """Test field validation and required fields."""
        dm = self.dependency_metadata_list[0]

        # Verify required fields are present
        assert dm.uuid is not None
        assert dm.meta is not None
        assert dm.meta.name is not None
        assert dm.spec is not None

        # Verify spec structure
        if dm.spec.dependency_data:
            assert dm.spec.dependency_data.project_uuid is not None
            assert dm.spec.dependency_data.package_name is not None
            assert dm.spec.dependency_data.package_version_uuid is not None

        if dm.spec.importer_data:
            assert dm.spec.importer_data.project_uuid is not None
            assert dm.spec.importer_data.package_name is not None
            assert dm.spec.importer_data.package_version_uuid is not None

    def test_dependency_metadata_pagination(self):
        """Test pagination capabilities."""
        # Test with page size
        paginated_results = dependency_metadata.list_dependency_metadata(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=5),
        )
        assert isinstance(paginated_results, list)
        assert len(paginated_results) > 0

    def test_dependency_metadata_error_handling(self):
        """Test error handling for invalid UUID."""
        # Test with invalid UUID
        invalid_dm = dependency_metadata.get_dependency_metadata(
            self.client, self.parent_namespace, "invalid-uuid"
        )
        assert invalid_dm is None

    def test_dependency_metadata_filter_by_project(self):
        """Test filtering dependency metadata by project UUID."""
        print("\n=== TESTING FILTER DEPENDENCY METADATA BY PROJECT ===")

        # Get first dependency metadata to extract project UUID
        if not self.dependency_metadata_list:
            pytest.skip("No dependency metadata available for filtering test")

        first_dm = self.dependency_metadata_list[0]
        if not first_dm.spec or not first_dm.spec.dependency_data:
            pytest.skip("Dependency metadata has no dependency_data")

        project_uuid = first_dm.spec.dependency_data.project_uuid

        # Filter dependency metadata by project
        list_params = ListParameters(
            filter=f'spec.dependency_data.project_uuid=="{project_uuid}"',
        )

        filtered_results = dependency_metadata.list_dependency_metadata(
            self.client, self.parent_namespace, list_params
        )

        assert isinstance(filtered_results, list), (
            "Should return a list of filtered dependency metadata"
        )
        assert len(filtered_results) > 0, (
            "Should have at least one dependency metadata for the project"
        )

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

    def test_dependency_metadata_ecosystem_distribution(self):
        """Test and analyze dependency metadata ecosystem distribution."""
        dependency_metadata_list = dependency_metadata.list_dependency_metadata(
            self.client, self.parent_namespace
        )

        ecosystem_counts = {}
        scope_counts = {}
        reachability_counts = {}

        for dm in dependency_metadata_list:
            if dm.spec and dm.spec.dependency_data:
                ecosystem = (
                    str(dm.spec.dependency_data.ecosystem)
                    if dm.spec.dependency_data.ecosystem
                    else "Unknown"
                )
                ecosystem_counts[ecosystem] = ecosystem_counts.get(ecosystem, 0) + 1

                scope = (
                    str(dm.spec.dependency_data.scope)
                    if dm.spec.dependency_data.scope
                    else "Unknown"
                )
                scope_counts[scope] = scope_counts.get(scope, 0) + 1

                reachability = (
                    str(dm.spec.dependency_data.reachability)
                    if dm.spec.dependency_data.reachability
                    else "Unknown"
                )
                reachability_counts[reachability] = (
                    reachability_counts.get(reachability, 0) + 1
                )

        print("\n=== Dependency Metadata Distribution ===")
        print("Ecosystem distribution:")
        for ecosystem, count in ecosystem_counts.items():
            print(f"  {ecosystem}: {count}")

        print("Scope distribution:")
        for scope, count in scope_counts.items():
            print(f"  {scope}: {count}")

        print("Reachability distribution:")
        for reachability, count in reachability_counts.items():
            print(f"  {reachability}: {count}")

        assert len(dependency_metadata_list) > 0

