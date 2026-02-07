"""Tests for AuthenticationLog resource operations."""

import pytest

from tests.conftest import TEST_MAX_PAGES_TRAVERSE


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

    def test_authentication_log_list(self) -> None:
        """LIST from tenant root with traverse (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        result = client.authentication_log.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_authentication_log_facade_get_raises_for_non_oss_namespace(self) -> None:
        """System-scoped get only when namespace is oss; otherwise use list."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        assert hasattr(client.authentication_log, "get")
        with pytest.raises(NotImplementedError, match="oss namespace"):
            client.authentication_log.get("any-uuid", namespace=self.root_namespace)
        with pytest.raises(NotImplementedError, match="oss namespace"):
            client.authentication_log.get("any-uuid")

    def test_authentication_log_module_get_returns_403(self) -> None:
        """Module-level get with system namespace returns 403 (assert as success)."""
        import endorlabs
        from endorlabs.exceptions import PermissionDeniedError
        from endorlabs.resources.authentication_log import get_authentication_log

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.authentication_log.list(
            traverse=True,
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
        with pytest.raises(PermissionDeniedError) as exc_info:
            get_authentication_log(self.client, ns, item.uuid)
        assert exc_info.value.status_code == 403

    def test_authentication_log_facade_has_no_create(self) -> None:
        """System-scoped facade has no create (system-owned)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        assert not hasattr(client.authentication_log, "create")
        with pytest.raises(AttributeError, match="create"):
            client.authentication_log.create({})
