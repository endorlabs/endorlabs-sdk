"""Tests for AuthenticationLog resource operations."""

import pytest

import endorlabs
from tests.conftest import (
    TEST_MAX_PAGES,
    TEST_PAGE_SIZE,
)


@pytest.mark.integration
@pytest.mark.long
class TestAuthenticationLog:
    """Test cases for AuthenticationLog resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace, root_namespace) -> None:
        """Set up test environment."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.endor_root_client = endorlabs.Client(
            tenant=root_namespace, api_client=api_client
        )

    def test_authentication_log_list(self) -> None:
        """LIST from namespace scope with bounded pagination."""
        result = self.endor_client.AuthenticationLog.list(
            page_size=TEST_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, list)

    def test_authentication_log_module_get_uses_item_namespace(self) -> None:
        """Facade get uses item namespace; backend auth decides access."""
        from endorlabs.core.exceptions import PermissionDeniedError

        items = self.endor_client.AuthenticationLog.list(
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
        with pytest.raises(PermissionDeniedError) as exc_info:
            self.endor_root_client.AuthenticationLog.get(item.uuid, namespace=ns)
        if hasattr(exc_info.value, "status_code"):
            assert exc_info.value.status_code == 403

    def test_authentication_log_facade_has_no_create(self) -> None:
        """System-scoped facade rejects create (system-owned, read-only)."""
        assert "create" not in self.endor_root_client.AuthenticationLog._supported_ops
        with pytest.raises(NotImplementedError, match="does not support create"):
            self.endor_root_client.AuthenticationLog.create(payload={})
