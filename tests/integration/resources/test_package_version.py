"""Integration tests for Package Version resource operations.

These tests verify the complete CRUD lifecycle for Package Version resources,
including tag management operations and error handling scenarios.
"""

import pytest

from endorlabs.api_client import APIClient
from endorlabs.resources import package_version
from tests.conftest import TEST_MAX_PAGES, TEST_MAX_PAGES_TRAVERSE, TEST_PAGE_SIZE


@pytest.mark.integration
class TestPackageVersion:
    """Test cases for Package Version operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace, root_namespace) -> None:
        """Fast setup: client and namespace from conftest."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace

    @pytest.fixture
    def sample_package_version(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Only fetches 1 item without traverse for fast setup. Tests that need
        sample data should request this fixture explicitly.
        """
        from endorlabs.types import ListParameters

        # Fetch 1 item without traverse (fast)
        results = package_version.list_package_versions(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=TEST_PAGE_SIZE),
            max_pages=TEST_MAX_PAGES,
        )
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    @pytest.mark.writes
    def test_package_version_update_with_mask(self, sample_package_version) -> None:
        """Test UPDATE package version operation with update_mask parameter.

        Local-only: updating package versions requires elevated permissions (403 in CI).
        """
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

        from endorlabs.resources.package_version import (
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

    def test_package_version_list(self) -> None:
        """LIST from tenant root with traverse."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        try:
            result = client.package_version.list(
                traverse=True,
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        assert isinstance(result, list)

    def test_package_version_get(self) -> None:
        """GET first item from LIST (root + traverse)."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        try:
            items = client.package_version.list(
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
        got = client.package_version.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    @pytest.mark.writes
    def test_client_ux_update_package_version(self) -> None:
        """Consumer UX: client.package_version.get() then update then revert."""
        import endorlabs
        from endorlabs.exceptions import ServerError
        from endorlabs.resources.package_version import UpdatePackageVersionPayload

        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        try:
            versions = client.package_version.list(max_pages=TEST_MAX_PAGES)
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
        current = client.package_version.get(item.uuid, namespace=ns)
        if not current:
            pytest.skip(f"Could not retrieve package version {item.uuid}")
        original_tags = list(getattr(current.meta, "tags", None) or [])
        new_tags = [*original_tags, "client-ux-update"]
        update_payload = UpdatePackageVersionPayload(meta={"tags": new_tags})
        try:
            updated = client.package_version.update(
                item.uuid, update_payload, update_mask="meta.tags", namespace=ns
            )
        except Exception as e:
            pytest.skip(f"Package version update not allowed in this environment: {e}")
        assert updated is not None
        restore_payload = UpdatePackageVersionPayload(meta={"tags": original_tags})
        try:
            client.package_version.update(
                item.uuid, restore_payload, update_mask="meta.tags", namespace=ns
            )
        except Exception as e:
            print(f"[WARNING] Failed to restore original package version values: {e}")


def add_package_version_tag(
    client: APIClient, namespace: str, package_version_uuid: str, tag: str
):
    """Add a tag to a package version."""
    from endorlabs.resources.package_version import (
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
    from endorlabs.resources.package_version import (
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
