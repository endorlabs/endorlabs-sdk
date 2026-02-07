"""Tests for EndorLicense resource operations."""

import pytest

from tests.conftest import TEST_MAX_PAGES_TRAVERSE


@pytest.mark.integration
@pytest.mark.long
class TestEndorLicense:
    """Test cases for EndorLicense resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace, root_namespace) -> None:
        """Set up test environment."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace

    def test_endor_license_list(self) -> None:
        """LIST from tenant root with traverse (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        result = client.endor_license.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_endor_license_spec_quota_and_license_configurations(self) -> None:
        """EndorLicense spec exposes quota and license_configurations when returned."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.endor_license.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        if item.spec is not None:
            assert hasattr(item.spec, "quota")
            assert hasattr(item.spec, "license_configurations")
            if item.spec.quota is not None and not isinstance(item.spec.quota, dict):
                assert hasattr(item.spec.quota, "max_daily_cloud_scans")
                assert hasattr(item.spec.quota, "max_daily_pr_scans")
            if item.spec.license_configurations is not None and not isinstance(
                item.spec.license_configurations, dict
            ):
                assert hasattr(
                    item.spec.license_configurations,
                    "security_review_configuration",
                )

    def test_endor_license_facade_get_raises_for_non_oss_namespace(self) -> None:
        """System-scoped get only when namespace is oss; otherwise use list."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        assert hasattr(client.endor_license, "get")
        with pytest.raises(NotImplementedError, match="oss namespace"):
            client.endor_license.get("any-uuid", namespace=self.root_namespace)
        with pytest.raises(NotImplementedError, match="oss namespace"):
            client.endor_license.get("any-uuid")

    def test_endor_license_module_get_returns_403(self) -> None:
        """Module-level get with system namespace returns 403 (assert as success)."""
        import endorlabs
        from endorlabs.exceptions import PermissionDeniedError
        from endorlabs.resources.endor_license import get_endor_license

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.endor_license.list(
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
            get_endor_license(self.client, ns, item.uuid)
        assert exc_info.value.status_code == 403

    def test_endor_license_facade_has_no_create(self) -> None:
        """System-scoped facade has no create (system-owned)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        assert not hasattr(client.endor_license, "create")
        with pytest.raises(AttributeError, match="create"):
            client.endor_license.create({})
