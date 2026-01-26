"""
Test cases for RepositoryVersion resource operations.

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
    def setup_fast(self):
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.tgowan-endor")

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

    def test_repository_version_get_list(self):
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

    def test_repository_version_get_by_uuid(self, sample_repository_version):
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

    def test_repository_version_conditional_attributes(self, sample_repository_version):
        """Test conditional attributes in repository version."""
        repository_version_obj = sample_repository_version

        # Check for conditional attributes
        if (
            hasattr(repository_version_obj, "context")
            and repository_version_obj.context
        ):
            print("RepositoryVersion has context attribute")
            assert isinstance(repository_version_obj.context, dict)
            assert "id" in repository_version_obj.context
            assert "type" in repository_version_obj.context

        if (
            hasattr(repository_version_obj, "scan_object")
            and repository_version_obj.scan_object
        ):
            print("RepositoryVersion has scan_object attribute")
            assert isinstance(repository_version_obj.scan_object, dict)
            assert "scan_time" in repository_version_obj.scan_object
            assert "status" in repository_version_obj.scan_object

    def test_repository_version_advanced_filtering(self, sample_repository_version):
        """Test advanced filtering capabilities."""
        from endor_cockpit.types import ListParameters

        # Test filtering by parent
        parent_uuid = sample_repository_version.meta.parent_uuid
        if parent_uuid:
            if parent_uuid:
                import conftest

                filtered_versions = repository_version.list_repository_versions(
                    self.client,
                    self.namespace,
                    list_params=ListParameters(
                        filter=f"meta.parent_uuid=={parent_uuid}",
                        page_size=conftest.TEST_PAGE_SIZE,
                    ),
                    max_pages=conftest.TEST_MAX_PAGES,
                )
                assert isinstance(filtered_versions, list)
        # Test field masking
        import conftest

        masked_versions = repository_version.list_repository_versions(
            self.client,
            self.namespace,
            list_params=ListParameters(
                mask="meta.name,spec.version",
                page_size=conftest.TEST_PAGE_SIZE,
            ),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(masked_versions, list)
        if masked_versions:
            version = masked_versions[0]
            # Should have masked fields
            assert hasattr(version, "meta")
            assert hasattr(version, "spec")

    def test_repository_version_error_handling(self):
        """Test error handling for invalid UUID."""
        # Test with invalid UUID
        invalid_repository_version = repository_version.get_repository_version(
            self.client, self.namespace, "invalid-uuid"
        )
        assert invalid_repository_version is None

    def test_repository_version_hierarchical_relationships(self, sample_repository_version):
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

    def test_repository_version_pagination(self):
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

    def test_repository_version_field_validation(self, sample_repository_version):
        """Test field validation and required fields."""
        repository_version_obj = sample_repository_version

        # Verify required fields are present
        assert repository_version_obj.uuid is not None
        assert repository_version_obj.meta.name is not None
        assert repository_version_obj.spec is not None

        # Verify version info structure if present
        if repository_version_obj.spec.version:
            version_info = repository_version_obj.spec.version
            # Version info can have ref, sha, or metadata
            assert hasattr(version_info, "ref") or hasattr(version_info, "sha")
