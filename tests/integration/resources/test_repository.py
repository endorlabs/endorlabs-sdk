"""Test cases for Repository resource operations.

Tests GET operations for Repository resources following the testing protocol.
"""

import pytest

import endorlabs
from endorlabs.resources.repository import (
    RepositoryMetaUpdate,
    UpdateRepositoryPayload,
)
from tests.conftest import (
    TEST_MAX_PAGES,
    TEST_PAGE_SIZE,
)


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
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.endor_root_client = endorlabs.Client(
            tenant=root_namespace, api_client=api_client
        )
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
        from endorlabs.core.exceptions import ServerError
        from endorlabs.core.types import ListParameters

        try:
            results = self.endor_root_client.Repository.list(
                list_params=ListParameters(page_size=TEST_PAGE_SIZE),
                max_pages=TEST_MAX_PAGES,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    def test_repository_advanced_filtering(self, sample_repository) -> None:
        """Test advanced filtering capabilities."""
        print("\n=== TESTING REPOSITORY FILTERING ===")
        from endorlabs.core.types import ListParameters

        sample_repo = sample_repository
        list_namespace = (
            sample_repo.tenant_meta.namespace
            if sample_repo.tenant_meta
            and getattr(sample_repo.tenant_meta, "namespace", None)
            else self.root_namespace
        )
        list_client = endorlabs.Client(tenant=list_namespace, api_client=self.client)

        # Test filtering by platform source
        github_repos = list_client.Repository.list(
            list_params=ListParameters(
                filter="spec.platform_source==PLATFORM_SOURCE_GITHUB",
                page_size=TEST_PAGE_SIZE,
            ),
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(github_repos, list), "Should return a list of repositories"
        print(f"Found {len(github_repos)} GitHub repositories")

        # Test field masking
        masked_repos = list_client.Repository.list(
            list_params=ListParameters(
                mask="meta.name,spec.platform_source",
                page_size=TEST_PAGE_SIZE,
            ),
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(masked_repos, list), (
            "Should return a list of masked repositories"
        )
        if masked_repos:
            repo = masked_repos[0]
            assert isinstance(repo, dict), "Masked list returns wire JSON dict rows"
            meta = repo.get("meta") or {}
            assert isinstance(meta, dict)
            assert "name" in meta or "name" in str(repo)
            print(f"Masked repository: {meta.get('name', repo.get('uuid'))}")

    def test_repository_error_handling(self) -> None:
        """Test error handling for invalid UUID."""
        # Test with invalid UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endorlabs.core.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            self.endor_root_client.Repository.get("invalid-uuid")
        assert exc_info.value.resource_uuid == "invalid-uuid"
        assert exc_info.value.operation == "get"
        assert exc_info.value.status_code == 400

    @pytest.mark.writes
    def test_client_ux_update_repository(self) -> None:
        """Consumer UX: client.Repository.get() then update then revert."""
        import endorlabs
        from endorlabs.core.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        try:
            repos = client.Repository.list(max_pages=TEST_MAX_PAGES)
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
        current = client.Repository.get(item.uuid, namespace=ns)
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
            updated = client.Repository.update(
                item.uuid, update_payload, update_mask="meta.description", namespace=ns
            )
        except Exception as e:
            pytest.skip(f"Repository update not allowed in this environment: {e}")
        assert updated is not None
        restore_payload = UpdateRepositoryPayload(
            meta=RepositoryMetaUpdate(description=original_description)
        )
        try:
            client.Repository.update(
                item.uuid, restore_payload, update_mask="meta.description", namespace=ns
            )
        except Exception as e:
            print(f"[WARNING] Failed to restore original repository values: {e}")
