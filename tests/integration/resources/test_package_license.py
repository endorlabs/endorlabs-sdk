"""Tests for PackageLicense resource operations."""

import pytest

import endorlabs
from tests.conftest import TEST_MAX_PAGES, TEST_PAGE_SIZE
from tests.integration.client.conftest import OSS_NAMESPACE


@pytest.mark.integration
class TestPackageLicense:
    """Test cases for PackageLicense resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace) -> None:
        """Set up test environment."""
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.namespace = namespace
        # Catalog rows are served from the literal ``oss`` namespace path (registry
        # scope is ``tenant`` because OpenAPI exposes both tenant and oss paths).
        self.catalog_client = endorlabs.Client(
            tenant=OSS_NAMESPACE, api_client=api_client
        )

    def test_package_license_list(self) -> None:
        """LIST on oss catalog plane (primary data path for PackageLicense)."""
        result = self.catalog_client.PackageLicense.list(
            page_size=TEST_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, list)
        if not result:
            pytest.skip(
                "No PackageLicense rows on oss catalog plane in this environment"
            )

    def test_package_license_get(self) -> None:
        """GET first oss catalog row from LIST."""
        items = self.catalog_client.PackageLicense.list(
            page_size=TEST_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES,
        )
        if not items:
            pytest.skip(
                "No PackageLicense rows on oss catalog plane in this environment"
            )
        item = items[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else OSS_NAMESPACE
        )
        got = self.catalog_client.PackageLicense.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid
