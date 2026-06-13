"""Tests for PackageLicense resource operations."""

import pytest

import endorlabs
from tests.conftest import TEST_MAX_PAGES, TEST_PAGE_SIZE


@pytest.mark.integration
@pytest.mark.long
class TestPackageLicense:
    """Test cases for PackageLicense resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace) -> None:
        """Set up test environment."""
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.namespace = namespace

    def test_package_license_list(self) -> None:
        """LIST in namespace (registry-based)."""
        result = self.endor_client.PackageLicense.list(
            page_size=TEST_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, list)

    def test_package_license_get(self) -> None:
        """GET first item from LIST if any (registry-based)."""
        items = self.endor_client.PackageLicense.list(
            page_size=TEST_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.namespace
        )
        got = self.endor_client.PackageLicense.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid
