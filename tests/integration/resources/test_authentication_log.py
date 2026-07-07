"""Tests for AuthenticationLog resource operations."""

import pytest

import endorlabs
from endorlabs.core.exceptions import PermissionDeniedError
from tests.integration.conftest import assert_bounded_log_rows, log_list_kwargs


@pytest.mark.integration
class TestAuthenticationLog:
    """Test cases for AuthenticationLog resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace, root_namespace) -> None:
        """Set up test environment."""
        self.namespace = namespace
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)

    def test_authentication_log_list(self) -> None:
        """LIST in namespace with bounded pagination (no traverse)."""
        result = self.endor_client.AuthenticationLog.list(**log_list_kwargs())
        assert isinstance(result, list)
        assert_bounded_log_rows(result)

    def test_authentication_log_module_get_uses_item_namespace(self) -> None:
        """Facade get uses item namespace; backend auth decides access."""
        items = self.endor_client.AuthenticationLog.list(**log_list_kwargs())
        assert_bounded_log_rows(items)
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        with pytest.raises(PermissionDeniedError) as exc_info:
            self.endor_client.AuthenticationLog.get(items[0])
        if hasattr(exc_info.value, "status_code"):
            assert exc_info.value.status_code == 403

    def test_authentication_log_facade_has_no_create(self) -> None:
        """Facade rejects create (read-only resource)."""
        assert "create" not in self.endor_client.AuthenticationLog._supported_ops
        with pytest.raises(NotImplementedError, match="does not support create"):
            self.endor_client.AuthenticationLog.create(payload={})
