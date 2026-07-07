"""Tests for CodeOwners resource operations."""

import pytest

from tests.conftest import TEST_MAX_PAGES, TEST_PAGE_SIZE


@pytest.mark.integration
class TestCodeOwners:
    """Test cases for CodeOwners resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace, root_namespace) -> None:
        """Set up test environment."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        import endorlabs

        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)

    def test_code_owners_list(self) -> None:
        """LIST in namespace (registry-based)."""
        result = self.endor_client.CodeOwners.list(
            page_size=TEST_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, list)

    def test_code_owners_get(self) -> None:
        """GET first item from LIST if any (registry-based)."""
        items = self.endor_client.CodeOwners.list(
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
        got = self.endor_client.CodeOwners.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    def test_code_owners_spec_version_has_ref_sha_metadata(self) -> None:
        """CodeOwners spec.version exposes ref, sha, metadata when returned."""
        items = self.endor_client.CodeOwners.list(
            page_size=TEST_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        if item.spec is not None and item.spec.version is not None:
            assert hasattr(item.spec.version, "ref")
            assert hasattr(item.spec.version, "sha")
            assert hasattr(item.spec.version, "metadata")
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.root_namespace
        )
        got = self.endor_client.CodeOwners.get(item.uuid, namespace=ns)
        if got and got.spec and got.spec.version is not None:
            assert hasattr(got.spec.version, "ref")
            assert hasattr(got.spec.version, "sha")
            assert hasattr(got.spec.version, "metadata")
