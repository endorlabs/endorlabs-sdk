"""Tests for VersionUpgrade resource operations."""

import pytest

from tests.conftest import TEST_MAX_PAGES_TRAVERSE, TEST_TRAVERSE_PAGE_SIZE


@pytest.mark.integration
@pytest.mark.long
class TestVersionUpgrade:
    """Test cases for VersionUpgrade resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace, root_namespace) -> None:
        """Set up test environment."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace

    def test_version_upgrade_list(self) -> None:
        """LIST from tenant root with traverse (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        result = client.VersionUpgrade.list(
            traverse=True,
            page_size=TEST_TRAVERSE_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_version_upgrade_get(self) -> None:
        """GET first item from LIST if any (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.VersionUpgrade.list(
            traverse=True,
            page_size=TEST_TRAVERSE_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.root_namespace
        )
        got = client.VersionUpgrade.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    def test_version_upgrade_create_raises_not_implemented(self) -> None:
        """Create is not supported; raises NotImplementedError."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        with pytest.raises(NotImplementedError, match="does not support create"):
            client.VersionUpgrade.create({})
