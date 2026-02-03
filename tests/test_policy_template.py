"""Tests for PolicyTemplate resource operations."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
tests_dir = Path(__file__).parent
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

import conftest


@pytest.mark.integration
@pytest.mark.long
class TestPolicyTemplate:
    """Test cases for PolicyTemplate resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace, root_namespace) -> None:
        """Set up test environment."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace

    def test_policy_template_list(self) -> None:
        """LIST from tenant root with traverse (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        result = client.policy_template.list(
            traverse=True,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_policy_template_facade_get_raises_for_non_oss_namespace(self) -> None:
        """SystemResourceFacade get only when namespace is oss; otherwise use list."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        assert hasattr(client.policy_template, "get")
        with pytest.raises(NotImplementedError, match="oss namespace"):
            client.policy_template.get("any-uuid", namespace=self.root_namespace)
        with pytest.raises(NotImplementedError, match="oss namespace"):
            client.policy_template.get("any-uuid")

    def test_policy_template_module_get_returns_403(self) -> None:
        """Module-level get with system namespace returns 403 (assert as success)."""
        import endorlabs
        from endorlabs.exceptions import PermissionDeniedError
        from endorlabs.resources.policy_template import get_policy_template

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.policy_template.list(
            traverse=True,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
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
            get_policy_template(self.client, ns, item.uuid)
        assert exc_info.value.status_code == 403

    def test_policy_template_facade_has_no_create(self) -> None:
        """SystemResourceFacade has no create (system-owned)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        assert not hasattr(client.policy_template, "create")
        with pytest.raises(AttributeError, match="create"):
            client.policy_template.create({})
