"""Integration tests for Package Version resource operations.

These tests verify the complete CRUD lifecycle for Package Version resources,
including tag management operations and error handling scenarios.
"""

import os

import conftest
import pytest

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import package_version


@pytest.mark.integration
class TestPackageVersion:
    """Test cases for Package Version operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self) -> None:
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

    @pytest.fixture
    def sample_package_version(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Only fetches 1 item without traverse for fast setup. Tests that need
        sample data should request this fixture explicitly.
        """
        from endor_cockpit.types import ListParameters

        # Fetch 1 item without traverse (fast)
        results = package_version.list_package_versions(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=1),
            max_pages=1,
        )
        if not results:
            pytest.skip("No package versions available for testing")
        return results[0]  # Return single item, not list

    def test_package_version_get_list(self) -> None:
        """Test GET package-versions operation."""
        import conftest

        from endor_cockpit.types import ListParameters

        package_versions_list = package_version.list_package_versions(
            self.client,
            self.namespace,
            list_params=ListParameters(
                page_size=conftest.TEST_PAGE_SIZE,
                traverse=True,
            ),
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(package_versions_list, list)
        assert len(package_versions_list) > 0

        # Verify structure
        for pv in package_versions_list:
            assert hasattr(pv, "uuid")
            assert hasattr(pv, "meta")
            assert hasattr(pv, "spec")
            assert hasattr(pv, "tenant_meta")

            # Verify meta fields
            assert hasattr(pv.meta, "name")
            assert hasattr(pv.meta, "description")
            assert hasattr(pv.meta, "create_time")
            assert hasattr(pv.meta, "created_by")
            assert hasattr(pv.meta, "update_time")
            assert hasattr(pv.meta, "updated_by")
            assert hasattr(pv.meta, "tags")

            # Verify spec fields
            assert hasattr(pv.spec, "package_name")
            assert hasattr(pv.spec, "ecosystem")
            assert hasattr(pv.spec, "language")
            assert hasattr(pv.spec, "project_uuid")

    def test_package_version_get_by_uuid(self, sample_package_version) -> None:
        """Test GET package-version by UUID operation."""
        test_package_version = sample_package_version
        # Use the package version's actual namespace
        package_namespace = (
            test_package_version.tenant_meta.namespace
            if test_package_version.tenant_meta
            else self.namespace
        )
        retrieved_package_version = package_version.get_package_version(
            self.client, package_namespace, test_package_version.uuid
        )
        assert retrieved_package_version is not None
        assert retrieved_package_version.uuid == test_package_version.uuid
        assert retrieved_package_version.meta.name == test_package_version.meta.name
        assert (
            retrieved_package_version.spec.package_name
            == test_package_version.spec.package_name
        )
        assert (
            retrieved_package_version.spec.ecosystem
            == test_package_version.spec.ecosystem
        )

    def test_package_version_update_with_mask(self, sample_package_version) -> None:
        """Test UPDATE package version operation with update_mask parameter."""
        print("\n=== TESTING PACKAGE VERSION UPDATE WITH MASK ===")

        package_version_uuid = sample_package_version.uuid
        # Use the package version's actual namespace
        package_namespace = (
            sample_package_version.tenant_meta.namespace
            if sample_package_version.tenant_meta
            else self.namespace
        )

        # Get current package version state
        current_pv = package_version.get_package_version(
            self.client, package_namespace, package_version_uuid
        )
        if not current_pv:
            pytest.skip(f"Could not retrieve package version {package_version_uuid}")

        # Store original values
        original_tags = current_pv.meta.tags or []
        original_description = current_pv.meta.description

        # Create update payload - only update safe fields
        new_tags = [*original_tags, "test-update", "mask-test"]
        new_description = (
            f"{original_description} [Updated by test]"
            if original_description
            else "Updated description for test"
        )

        from pydantic import BaseModel

        from endor_cockpit.resources.package_version import (
            UpdatePackageVersionPayload,
        )

        class MetaUpdate(BaseModel):
            description: str
            tags: list[str]

        update_payload = UpdatePackageVersionPayload(
            meta=MetaUpdate(description=new_description, tags=new_tags).model_dump()
        )

        print(f"Updating package version: {package_version_uuid}")
        print(f"New description: {new_description}")
        print(f"New tags: {new_tags}")

        # Update the package version with update_mask
        updated_pv = package_version.update_package_version(
            self.client,
            package_namespace,
            package_version_uuid,
            update_payload,
            "meta.description,meta.tags",
        )

        assert updated_pv is not None, "Package version update should succeed"
        assert updated_pv.meta.description == new_description, (
            "Package version description should be updated"
        )
        assert "test-update" in updated_pv.meta.tags, "Updated tag should be present"
        assert "mask-test" in updated_pv.meta.tags, "Updated tag should be present"

        print(f"[SUCCESS] Package version updated: {updated_pv.uuid}")
        print(f"Updated description: {updated_pv.meta.description}")
        print(f"Updated tags: {updated_pv.meta.tags}")

        # Restore original values if possible
        class MetaRestore(BaseModel):
            description: str | None
            tags: list[str]

        restore_payload = UpdatePackageVersionPayload(
            meta=MetaRestore(
                description=original_description, tags=original_tags
            ).model_dump()
        )
        try:
            package_version.update_package_version(
                self.client,
                package_namespace,
                package_version_uuid,
                restore_payload,
                "meta.description,meta.tags",
            )
            print("[CLEANUP] Restored original package version values")
        except Exception as e:
            print(f"[WARNING] Failed to restore original values: {e}")


def add_package_version_tag(
    client: APIClient, namespace: str, package_version_uuid: str, tag: str
):
    """Add a tag to a package version."""
    from endor_cockpit.resources.package_version import (
        UpdatePackageVersionPayload,
        update_package_version,
    )

    # Get current package version
    current_pv = package_version.get_package_version(
        client, namespace, package_version_uuid
    )
    if not current_pv:
        return None

    # Add tag to existing tags
    current_tags = current_pv.meta.tags or []
    if tag not in current_tags:
        current_tags.append(tag)

    # Update with new tags - create a minimal meta object with just tags

    from pydantic import BaseModel

    class MetaUpdate(BaseModel):
        tags: list[str]

    payload = UpdatePackageVersionPayload(
        meta=MetaUpdate(tags=current_tags).model_dump()
    )
    return update_package_version(
        client, namespace, package_version_uuid, payload, "meta.tags"
    )


def remove_package_version_tag(
    client: APIClient, namespace: str, package_version_uuid: str, tag: str
):
    """Remove a tag from a package version."""
    from endor_cockpit.resources.package_version import (
        UpdatePackageVersionPayload,
        update_package_version,
    )

    # Get current package version
    current_pv = package_version.get_package_version(
        client, namespace, package_version_uuid
    )
    if not current_pv:
        return None

    # Remove tag from existing tags
    current_tags = current_pv.meta.tags or []
    if tag in current_tags:
        current_tags.remove(tag)

    # Update with modified tags - create a minimal meta object with just tags

    from pydantic import BaseModel

    class MetaUpdate(BaseModel):
        tags: list[str]

    payload = UpdatePackageVersionPayload(
        meta=MetaUpdate(tags=current_tags).model_dump()
    )
    return update_package_version(
        client, namespace, package_version_uuid, payload, "meta.tags"
    )


def list_package_version_tags(
    client: APIClient, namespace: str, package_version_uuid: str
):
    """List tags for a package version."""
    pv = package_version.get_package_version(client, namespace, package_version_uuid)
    return pv.meta.tags if pv and pv.meta.tags else []
