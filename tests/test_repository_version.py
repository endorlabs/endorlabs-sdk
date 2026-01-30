"""Test cases for RepositoryVersion resource operations.

Tests GET operations for RepositoryVersion resources following the testing protocol.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import repository_version


@pytest.mark.integration
class TestRepositoryVersion:
    """Test cases for RepositoryVersion resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self) -> None:
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        import conftest

        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

    @pytest.fixture
    def sample_repository_version(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Only fetches 1 item for fast setup. Tests that need sample data should
        request this fixture explicitly.
        """
        from endor_cockpit.types import ListParameters

        results = repository_version.list_repository_versions(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=1),
            max_pages=1,
        )
        if not results:
            pytest.skip("No repository versions available for testing")
        return results[0]  # Return single item, not list

    def test_repository_version_get_list(self) -> None:
        """Test GET repository versions operation."""
        print("\n=== TESTING GET REPOSITORY VERSIONS ===")

        # Test list_repository_versions with pagination limits
        import conftest

        from endor_cockpit.types import ListParameters

        repository_versions_list = repository_version.list_repository_versions(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(repository_versions_list, list), (
            "Should return a list of repository versions"
        )
        assert len(repository_versions_list) > 0, (
            "Should have at least one repository version"
        )

        print(f"Found {len(repository_versions_list)} repository versions")

        # Display first few repository versions
        for i, repo_version in enumerate(repository_versions_list[:3]):
            print(f"Repository Version {i + 1}:")
            print(f"  UUID: {repo_version.uuid}")
            print(f"  Name: {repo_version.meta.name}")
            print(f"  Kind: {repo_version.meta.kind}")
            print(f"  Version: {repo_version.spec.version}")
            print(f"  Parent UUID: {repo_version.meta.parent_uuid}")

    def test_repository_version_get_by_uuid(self, sample_repository_version) -> None:
        """Test GET repository version by UUID operation."""
        test_repository_version = sample_repository_version
        retrieved_repository_version = repository_version.get_repository_version(
            self.client, self.namespace, test_repository_version.uuid
        )
        assert retrieved_repository_version is not None
        assert retrieved_repository_version.uuid == test_repository_version.uuid
        assert (
            retrieved_repository_version.meta.name == test_repository_version.meta.name
        )

    def test_repository_version_error_handling(self) -> None:
        """Test error handling for invalid UUID."""
        # Test with invalid UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endor_cockpit.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            repository_version.get_repository_version(
                self.client, self.namespace, "invalid-uuid"
            )
        assert exc_info.value.resource_uuid == "invalid-uuid"
        assert exc_info.value.operation == "get"
        assert exc_info.value.status_code == 400

    def test_repository_version_hierarchical_relationships(
        self, sample_repository_version
    ) -> None:
        """Test hierarchical relationships in repository version."""
        repository_version_obj = sample_repository_version

        # Test parent relationship
        if (
            hasattr(repository_version_obj.meta, "parent_uuid")
            and repository_version_obj.meta.parent_uuid
        ):
            parent_uuid = repository_version_obj.meta.parent_uuid
            assert isinstance(parent_uuid, str)
            assert len(parent_uuid) > 0

        if (
            hasattr(repository_version_obj.meta, "parent_kind")
            and repository_version_obj.meta.parent_kind
        ):
            parent_kind = repository_version_obj.meta.parent_kind
            assert isinstance(parent_kind, str)
            assert parent_kind == "Project"

    def test_repository_version_pagination(self) -> None:
        """Test pagination capabilities."""
        import conftest

        from endor_cockpit.types import ListParameters

        # Test with page size
        # Note: API may return more than page_size if it has a minimum page size
        paginated_versions = repository_version.list_repository_versions(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=5),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(paginated_versions, list)
        assert len(paginated_versions) > 0

    def test_repository_version_advanced_filtering(self) -> None:
        """Test advanced filtering capabilities."""
        print("\n=== TESTING REPOSITORY VERSION FILTERING ===")
        import conftest

        from endor_cockpit.types import ListParameters

        # Test filtering by parent UUID (if we have a sample)
        # First get a sample to use its parent UUID
        sample_results = repository_version.list_repository_versions(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=1),
            max_pages=1,
        )
        if sample_results and sample_results[0].meta.parent_uuid:
            parent_uuid = sample_results[0].meta.parent_uuid
            filtered_versions = repository_version.list_repository_versions(
                self.client,
                self.namespace,
                list_params=ListParameters(
                    filter=f'meta.parent_uuid=="{parent_uuid}"',
                    page_size=conftest.TEST_PAGE_SIZE,
                ),
                max_pages=conftest.TEST_MAX_PAGES,
            )
            assert isinstance(filtered_versions, list), (
                "Should return a list of repository versions"
            )
            print(
                f"Found {len(filtered_versions)} repository versions "
                f"for parent {parent_uuid}"
            )

        # Test field masking
        masked_versions = repository_version.list_repository_versions(
            self.client,
            self.namespace,
            list_params=ListParameters(
                mask="meta.name,spec.version",
                page_size=conftest.TEST_PAGE_SIZE,
            ),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(masked_versions, list), (
            "Should return a list of masked repository versions"
        )
        if masked_versions:
            version = masked_versions[0]
            # Should have masked fields
            assert hasattr(version, "meta")
            assert hasattr(version, "spec")
            print(f"Masked repository version: {version.meta.name}")
