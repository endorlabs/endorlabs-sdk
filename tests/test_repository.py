"""
Test cases for Repository resource operations.

Tests GET operations for Repository resources following the testing protocol.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import repository


@pytest.mark.integration
class TestRepository:
    """Test cases for Repository resource operations."""

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

        from endor_cockpit.types import ListParameters

        self.repositories = repository.list_repositories(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
        )
        if not self.repositories:
            pytest.skip("No repositories available for testing")

    def test_repository_get_list(self):
        """Test GET repositories operation."""
        print("\n=== TESTING GET REPOSITORIES ===")

        # Test list_repositories
        repositories_list = repository.list_repositories(self.client, self.namespace)
        assert isinstance(repositories_list, list), (
            "Should return a list of repositories"
        )
        assert len(repositories_list) > 0, "Should have at least one repository"

        print(f"Found {len(repositories_list)} repositories")

        # Display first few repositories
        for i, repo in enumerate(repositories_list[:3]):
            print(f"Repository {i + 1}:")
            print(f"  UUID: {repo.uuid}")
            print(f"  Name: {repo.meta.name}")
            print(f"  Kind: {repo.meta.kind}")
            print(f"  Platform: {repo.spec.platform_source}")
            print(f"  Clone URL: {repo.spec.http_clone_url}")

    def test_repository_get_by_uuid(self):
        """Test GET repository by UUID operation."""
        test_repository = self.repositories[0]
        retrieved_repository = repository.get_repository(
            self.client, self.namespace, test_repository.uuid
        )
        assert retrieved_repository is not None
        assert retrieved_repository.uuid == test_repository.uuid
        assert retrieved_repository.meta.name == test_repository.meta.name

    def test_repository_conditional_attributes(self):
        """Test conditional attributes in repository."""
        repository_obj = self.repositories[0]

        # Check for conditional attributes
        if (
            hasattr(repository_obj, "ingested_object")
            and repository_obj.ingested_object
        ):
            print("Repository has ingested_object attribute")
            assert isinstance(repository_obj.ingested_object, dict)
            assert "ingestion_time" in repository_obj.ingested_object
            assert "raw" in repository_obj.ingested_object

    def test_repository_advanced_filtering(self):
        """Test advanced filtering capabilities."""
        from endor_cockpit.types import ListParameters

        # Test filtering by platform
        github_repos = repository.list_repositories(
            self.client,
            self.namespace,
            list_params=ListParameters(
                filter="spec.platform_source==PLATFORM_SOURCE_GITHUB"
            ),
        )
        assert isinstance(github_repos, list)

        # Test field masking
        masked_repos = repository.list_repositories(
            self.client,
            self.namespace,
            list_params=ListParameters(mask="meta.name,spec.platform_source"),
        )
        assert isinstance(masked_repos, list)
        if masked_repos:
            repo = masked_repos[0]
            # Should have masked fields
            assert hasattr(repo, "meta")
            assert hasattr(repo, "spec")

    def test_repository_error_handling(self):
        """Test error handling for invalid UUID."""
        # Test with invalid UUID
        invalid_repository = repository.get_repository(
            self.client, self.namespace, "invalid-uuid"
        )
        assert invalid_repository is None
