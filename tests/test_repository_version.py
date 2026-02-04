"""Test cases for RepositoryVersion resource operations.

Tests GET operations for RepositoryVersion resources following the testing protocol.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import conftest

from endorlabs.resources import repository_version
from endorlabs.resources.repository_version import (
    RepositoryVersionMetaUpdate,
    UpdateRepositoryVersionPayload,
)


@pytest.mark.integration
class TestRepositoryVersion:
    """Test cases for RepositoryVersion resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace, root_namespace) -> None:
        """Fast setup: client and namespace from conftest."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace

    @pytest.fixture
    def sample_repository_version(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Only fetches 1 item for fast setup. Tests that need sample data should
        request this fixture explicitly.
        """
        from endorlabs.exceptions import ServerError
        from endorlabs.types import ListParameters

        try:
            results = repository_version.list_repository_versions(
                self.client,
                self.namespace,
                list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
                max_pages=conftest.TEST_MAX_PAGES,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    def test_repository_version_error_handling(self) -> None:
        """Test error handling for invalid UUID."""
        # Test with invalid UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endorlabs.exceptions import ValidationError

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

    def test_repository_version_list(self) -> None:
        """LIST from tenant root with traverse."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        try:
            result = client.repository_version.list(
                traverse=True,
                max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        assert isinstance(result, list)

    def test_repository_version_list_with_parent_project(self) -> None:
        """LIST repository versions with parent=project (list with parent resource)."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        try:
            projects = client.project.list(
                traverse=True,
                max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list projects); skip")
        if not projects:
            pytest.skip("No projects in scope (empty; may be filter/auth/scope)")
        project = projects[0]
        try:
            result = client.repository_version.list(
                parent=project,
                traverse=True,
                max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        assert isinstance(result, list)

    def test_repository_version_get(self) -> None:
        """GET first item from LIST (root + traverse)."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        try:
            items = client.repository_version.list(
                traverse=True,
                max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
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
        got = client.repository_version.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    def test_repository_version_scan_object_has_status_scan_time(self) -> None:
        """RepositoryVersion scan_object exposes status and scan_time when present."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        try:
            items = client.repository_version.list(
                traverse=True,
                max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        if item.scan_object is not None and not isinstance(item.scan_object, dict):
            assert hasattr(item.scan_object, "status")
            assert hasattr(item.scan_object, "scan_time")
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.root_namespace
        )
        got = client.repository_version.get(item.uuid, namespace=ns)
        if (
            got
            and got.scan_object is not None
            and not isinstance(got.scan_object, dict)
        ):
            assert hasattr(got.scan_object, "status")
            assert hasattr(got.scan_object, "scan_time")

    def test_repository_version_advanced_filtering(self) -> None:
        """Test advanced filtering capabilities."""
        print("\n=== TESTING REPOSITORY VERSION FILTERING ===")
        import conftest

        from endorlabs.types import ListParameters

        # Test filtering by parent UUID (if we have a sample)
        # First get a sample to use its parent UUID
        sample_results = repository_version.list_repository_versions(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
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

    @pytest.mark.writes
    def test_client_ux_update_repository_version(self) -> None:
        """Consumer UX: client.repository_version.get() then update then revert."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        try:
            versions = client.repository_version.list(max_pages=conftest.TEST_MAX_PAGES)
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not versions:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = versions[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.namespace
        )
        current = client.repository_version.get(item.uuid, namespace=ns)
        if not current:
            pytest.skip(f"Could not retrieve repository version {item.uuid}")
        original_description = getattr(current.meta, "description", None) or ""
        new_description = (
            f"{original_description} [client-ux]"
            if original_description
            else "client-ux"
        )
        update_payload = UpdateRepositoryVersionPayload(
            meta=RepositoryVersionMetaUpdate(description=new_description)
        )
        try:
            updated = client.repository_version.update(
                item.uuid,
                update_payload,
                update_mask="meta.description",
                namespace=ns,
            )
        except Exception as e:
            pytest.skip(
                f"Repository version update not allowed in this environment: {e}"
            )
        assert updated is not None
        restore_payload = UpdateRepositoryVersionPayload(
            meta=RepositoryVersionMetaUpdate(description=original_description)
        )
        try:
            client.repository_version.update(
                item.uuid,
                restore_payload,
                update_mask="meta.description",
                namespace=ns,
            )
        except Exception as e:
            print(
                f"[WARNING] Failed to restore original repository version values: {e}"
            )
