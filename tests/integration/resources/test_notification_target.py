"""Tests for NotificationTarget resource operations."""

import pytest

from tests.conftest import TEST_MAX_PAGES_TRAVERSE, TEST_TRAVERSE_PAGE_SIZE


@pytest.mark.integration
@pytest.mark.long
class TestNotificationTarget:
    """Test cases for NotificationTarget resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace, root_namespace) -> None:
        """Set up test environment."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace

    def test_notification_target_list(self) -> None:
        """LIST from tenant root with traverse (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        result = client.NotificationTarget.list(
            traverse=True,
            page_size=TEST_TRAVERSE_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_notification_target_get(self) -> None:
        """GET first item from LIST (root + traverse) (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.NotificationTarget.list(
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
        got = client.NotificationTarget.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    def test_notification_target_spec_action_has_action_type(self) -> None:
        """NotificationTarget spec.action exposes action_type when present."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.NotificationTarget.list(
            traverse=True,
            page_size=TEST_TRAVERSE_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        if item.spec is not None and item.spec.action is not None:
            act = item.spec.action
            if not isinstance(act, dict):
                assert hasattr(act, "action_type")
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.root_namespace
        )
        got = client.NotificationTarget.get(item.uuid, namespace=ns)
        if (
            got
            and got.spec
            and got.spec.action is not None
            and not isinstance(got.spec.action, dict)
        ):
            assert hasattr(got.spec.action, "action_type")
