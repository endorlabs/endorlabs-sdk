"""Tests for EndorLicense resource operations."""

import pytest

import endorlabs
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
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.endor_root_client = endorlabs.Client(
            tenant=root_namespace, api_client=api_client
        )

    def test_endor_license_list(self) -> None:
        """LIST from tenant root with traverse (registry-based)."""
        result = self.endor_root_client.endor_license.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_endor_license_spec_quota_and_license_configurations(self) -> None:
        """EndorLicense spec exposes quota and license_configurations when returned."""
        items = self.endor_root_client.endor_license.list(
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
        assert hasattr(self.endor_root_client.endor_license, "get")
        with pytest.raises(NotImplementedError, match="oss namespace"):
            self.endor_root_client.endor_license.get(
                "any-uuid", namespace=self.root_namespace
            )
        with pytest.raises(NotImplementedError, match="oss namespace"):
            self.endor_root_client.endor_license.get("any-uuid")

    def test_endor_license_module_get_returns_403(self) -> None:
        """Facade get with non-oss namespace raises NotImplementedError or 403."""
        from endorlabs.exceptions import PermissionDeniedError

        items = self.endor_root_client.endor_license.list(
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
        with pytest.raises((PermissionDeniedError, NotImplementedError)) as exc_info:
            self.endor_root_client.endor_license.get(item.uuid, namespace=ns)
        if hasattr(exc_info.value, "status_code"):
            assert exc_info.value.status_code == 403

    def test_endor_license_facade_has_no_create(self) -> None:
        """System-scoped facade rejects create (system-owned, read-only)."""
        assert "create" not in self.endor_root_client.endor_license._supported_ops
        with pytest.raises(NotImplementedError, match="does not support create"):
            self.endor_root_client.endor_license.create(payload={})
