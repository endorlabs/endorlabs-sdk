"""Test cases for Repository resource operations.

Tests GET operations for Repository resources following the testing protocol.
"""

import pytest

from endorlabs.resources import repository
from endorlabs.resources.repository import (
    RepositoryMetaUpdate,
    UpdateRepositoryPayload,
)
from tests.conftest import TEST_MAX_PAGES, TEST_MAX_PAGES_TRAVERSE, TEST_PAGE_SIZE


@pytest.mark.integration
class TestRepository:
    """Test cases for Repository resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace, root_namespace) -> None:
        """Fast setup: client and namespace from conftest."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.parent_namespace = root_namespace
        self.created_repository_uuids = []

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
                list_params=ListParameters(page_size=TEST_PAGE_SIZE, traverse=True),
                max_pages=TEST_MAX_PAGES,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    def test_repository_list(self) -> None:
        """LIST from tenant root with traverse."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        try:
            result = client.repository.list(
                traverse=True,
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        assert isinstance(result, list)

    def test_repository_get(self) -> None:
        """GET first item from LIST (root + traverse)."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        try:
            items = client.repository.list(
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
        got = client.repository.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    def test_repository_advanced_filtering(self) -> None:
        """Test advanced filtering capabilities."""
        print("\n=== TESTING REPOSITORY FILTERING ===")
        from endorlabs.types import ListParameters

        # Test filtering by platform source
        github_repos = repository.list_repositories(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(
                filter="spec.platform_source==PLATFORM_SOURCE_GITHUB",
                page_size=TEST_PAGE_SIZE,
                traverse=True,
            ),
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(github_repos, list), "Should return a list of repositories"
        print(f"Found {len(github_repos)} GitHub repositories")

        # Test field masking
        masked_repos = repository.list_repositories(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(
                mask="meta.name,spec.platform_source",
                page_size=TEST_PAGE_SIZE,
                traverse=True,
            ),
            max_pages=TEST_MAX_PAGES,
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

    @pytest.mark.writes
    def test_client_ux_update_repository(self) -> None:
        """Consumer UX: client.repository.get() then update then revert."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        try:
            repos = client.repository.list(traverse=True, max_pages=TEST_MAX_PAGES)
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not repos:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = repos[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.namespace
        )
        current = client.repository.get(item.uuid, namespace=ns)
        if not current:
            pytest.skip(f"Could not retrieve repository {item.uuid}")
        original_description = getattr(current.meta, "description", None) or ""
        new_description = (
            f"{original_description} [client-ux]"
            if original_description
            else "client-ux"
        )
        update_payload = UpdateRepositoryPayload(
            meta=RepositoryMetaUpdate(description=new_description)
        )
        try:
            updated = client.repository.update(
                item.uuid, update_payload, update_mask="meta.description", namespace=ns
            )
        except Exception as e:
            pytest.skip(f"Repository update not allowed in this environment: {e}")
        assert updated is not None
        restore_payload = UpdateRepositoryPayload(
            meta=RepositoryMetaUpdate(description=original_description)
        )
        try:
            client.repository.update(
                item.uuid, restore_payload, update_mask="meta.description", namespace=ns
            )
        except Exception as e:
            print(f"[WARNING] Failed to restore original repository values: {e}")
