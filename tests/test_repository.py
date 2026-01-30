"""Test cases for Repository resource operations.

Tests GET operations for Repository resources following the testing protocol.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endorlabs.api_client import APIClient
from endorlabs.resources import repository


@pytest.mark.integration
class TestRepository:
    """Test cases for Repository resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self) -> None:
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        import conftest

        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Track created resources for cleanup
        # (repositories are read-only, but establish pattern)
        self.created_repository_uuids = []

        # Get test data - use parent namespace to access child resources
        parts = self.namespace.split(".")
        self.parent_namespace = parts[0] if len(parts) > 1 else self.namespace

    def teardown_method(self) -> None:
        """Clean up any resources created during tests."""
        # Repositories are read-only and cannot be deleted, but we establish the pattern
        # for consistency and future use if repositories become deletable
        if hasattr(self, "created_repository_uuids"):
            # Note: Repositories cannot be deleted via API, so cleanup is a no-op
            # This method exists to maintain consistent test structure
            self.created_repository_uuids.clear()

    @pytest.fixture
    def sample_repository(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Only fetches 1 item for fast setup. Tests that need sample data should
        request this fixture explicitly.
        """
        from endorlabs.exceptions import ServerError
        from endorlabs.types import ListParameters

        try:
            results = repository.list_repositories(
                self.client,
                self.parent_namespace,
                list_params=ListParameters(page_size=1, traverse=True),
                max_pages=1,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    def test_repository_get_list(self) -> None:
        """Test GET repositories operation."""
        print("\n=== TESTING GET REPOSITORIES ===")

        import conftest

        from endorlabs.exceptions import ServerError
        from endorlabs.types import ListParameters

        try:
            repositories_list = repository.list_repositories(
                self.client,
                self.parent_namespace,
                list_params=ListParameters(
                    page_size=conftest.TEST_PAGE_SIZE,
                    traverse=True,
                ),
                max_pages=conftest.TEST_MAX_PAGES,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        assert isinstance(repositories_list, list), (
            "Should return a list of repositories"
        )
        if len(repositories_list) == 0:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

        print(f"Found {len(repositories_list)} repositories")

        # Display first few repositories
        for i, repo in enumerate(repositories_list[:3]):
            print(f"Repository {i + 1}:")
            print(f"  UUID: {repo.uuid}")
            print(f"  Name: {repo.meta.name}")
            print(f"  Kind: {repo.meta.kind}")
            print(f"  Platform: {repo.spec.platform_source}")
            print(f"  Clone URL: {repo.spec.http_clone_url}")

    def test_repository_get_by_uuid(self, sample_repository) -> None:
        """Test GET repository by UUID operation."""
        test_repository = sample_repository
        # Use the repository's actual namespace
        # (may be in child namespace when traverse=True)
        repository_namespace = (
            test_repository.tenant_meta.namespace
            if test_repository.tenant_meta
            else self.parent_namespace
        )
        retrieved_repository = repository.get_repository(
            self.client, repository_namespace, test_repository.uuid
        )
        assert retrieved_repository is not None
        assert retrieved_repository.uuid == test_repository.uuid
        assert retrieved_repository.meta.name == test_repository.meta.name

    def test_repository_advanced_filtering(self) -> None:
        """Test advanced filtering capabilities."""
        print("\n=== TESTING REPOSITORY FILTERING ===")
        import conftest

        from endorlabs.types import ListParameters

        # Test filtering by platform source
        github_repos = repository.list_repositories(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(
                filter="spec.platform_source==PLATFORM_SOURCE_GITHUB",
                page_size=conftest.TEST_PAGE_SIZE,
                traverse=True,
            ),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(github_repos, list), "Should return a list of repositories"
        print(f"Found {len(github_repos)} GitHub repositories")

        # Test field masking
        masked_repos = repository.list_repositories(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(
                mask="meta.name,spec.platform_source",
                page_size=conftest.TEST_PAGE_SIZE,
                traverse=True,
            ),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(masked_repos, list), (
            "Should return a list of masked repositories"
        )
        if masked_repos:
            repo = masked_repos[0]
            # Should have masked fields
            assert hasattr(repo, "meta")
            assert hasattr(repo, "spec")
            print(f"Masked repository: {repo.meta.name}")

    def test_repository_error_handling(self) -> None:
        """Test error handling for invalid UUID."""
        # Test with invalid UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endorlabs.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            repository.get_repository(
                self.client, self.parent_namespace, "invalid-uuid"
            )
        assert exc_info.value.resource_uuid == "invalid-uuid"
        assert exc_info.value.operation == "get"
        assert exc_info.value.status_code == 400

    def test_client_recommended_ux_list_repositories(self) -> None:
        """Recommended UX: endorlabs.Client(tenant=...); client.repositories.list()."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.namespace,
            max_retries=2,
            backoff_factor=0.1,
            auth_method="api-key",
        )
        repositories = client.repositories.list(max_pages=1)
        assert isinstance(repositories, list)
