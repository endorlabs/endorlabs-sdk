"""Tests for VersionUpgrade resource operations."""

import pytest

from tests.conftest import TEST_MAX_PAGES, TEST_PAGE_SIZE


@pytest.mark.integration
class TestVersionUpgrade:
    """Test cases for VersionUpgrade resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace, root_namespace) -> None:
        """Set up test environment."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        import endorlabs

        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)

    def test_version_upgrade_list(self) -> None:
        """LIST in namespace (registry-based)."""
        result = self.endor_client.VersionUpgrade.list(
            page_size=TEST_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, list)

    def test_version_upgrade_get(self) -> None:
        """GET first item from LIST if any (registry-based)."""
        items = self.endor_client.VersionUpgrade.list(
            page_size=TEST_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.root_namespace
        )
        got = self.endor_client.VersionUpgrade.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    def test_version_upgrade_create_raises_not_implemented(self) -> None:
        """Create is not supported; raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="does not support create"):
            self.endor_client.VersionUpgrade.create({})
