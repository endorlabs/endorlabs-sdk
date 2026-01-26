"""
Integration tests for Package Version resource operations.

These tests verify the complete CRUD lifecycle for Package Version resources,
including tag management operations and error handling scenarios.
"""

import os

import pytest

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import package_version


@pytest.mark.integration
class TestPackageVersion:
    """Test cases for Package Version operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self):
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.tgowan-endor")

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

    def test_package_version_get_list(self):
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

    def test_package_version_get_by_uuid(self, sample_package_version):
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
    from typing import List

    from pydantic import BaseModel

    class MetaUpdate(BaseModel):
        tags: List[str]

    payload = UpdatePackageVersionPayload(
        meta=MetaUpdate(tags=current_tags).model_dump()
    )
    return update_package_version(
        client, namespace, package_version_uuid, payload, ["meta.tags"]
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
    from typing import List

    from pydantic import BaseModel

    class MetaUpdate(BaseModel):
        tags: List[str]

    payload = UpdatePackageVersionPayload(
        meta=MetaUpdate(tags=current_tags).model_dump()
    )
    return update_package_version(
        client, namespace, package_version_uuid, payload, ["meta.tags"]
    )


def list_package_version_tags(
    client: APIClient, namespace: str, package_version_uuid: str
):
    """List tags for a package version."""
    pv = package_version.get_package_version(client, namespace, package_version_uuid)
    return pv.meta.tags if pv and pv.meta.tags else []
