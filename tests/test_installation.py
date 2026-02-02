"""Test cases for Installation resource operations.

Tests GET operations for Installation resources.
Installations are read-only resources managed by platform integrations.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import conftest

from endorlabs.resources import installation
from endorlabs.types import ListParameters


@pytest.mark.integration
class TestInstallation:
    """Test cases for Installation resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace, root_namespace) -> None:
        """Fast setup: client and namespace from conftest."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.tenant_root = root_namespace

    @pytest.fixture
    def sample_installation(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Uses traverse=True to search across all namespaces, matching the
        pattern used in test_installation_list.
        """
        from endorlabs.exceptions import ServerError

        try:
            results = installation.list_installations(
                self.client,
                self.tenant_root,
                list_params=ListParameters(
                    traverse=True, page_size=conftest.TEST_PAGE_SIZE
                ),
                max_pages=conftest.TEST_MAX_PAGES,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    def test_installation_list(self) -> None:
        """LIST from tenant root with traverse."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        result = client.installation.list(
            traverse=True,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_installation_get(self) -> None:
        """GET first item from LIST (root + traverse)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.installation.list(
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
        got = client.installation.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    def test_installation_filter_by_platform(self, sample_installation) -> None:
        """Test filtering installations by platform type."""
        print("\n=== TESTING FILTER INSTALLATIONS BY PLATFORM ===")

        # Get first installation to extract platform type
        first_installation = sample_installation
        if not first_installation.spec or not first_installation.spec.platform_type:
            pytest.skip("Installation has no platform_type")

        platform_type = first_installation.spec.platform_type
        # API expects the enum string value (e.g. PLATFORM_SOURCE_GITHUB), not the
        # Python enum name (e.g. PlatformSourceType.GITHUB).
        platform_type_value = (
            platform_type.value
            if hasattr(platform_type, "value")
            else str(platform_type)
        )

        # Filter installations by platform (tenant root + traverse for tenant-wide)
        list_params = ListParameters(
            filter=f'spec.platform_type=="{platform_type_value}"',
            traverse=True,
        )

        filtered_results = installation.list_installations(
            self.client, self.tenant_root, list_params
        )

        assert isinstance(filtered_results, list), (
            "Should return a list of filtered installations"
        )
        if len(filtered_results) == 0:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

        # Verify all results have the same platform (compare by API value)
        for result in filtered_results:
            if result.spec and result.spec.platform_type:
                result_value = (
                    result.spec.platform_type.value
                    if hasattr(result.spec.platform_type, "value")
                    else str(result.spec.platform_type)
                )
                assert result_value == platform_type_value, (
                    "All filtered results should have the same platform"
                )

        print(
            f"Found {len(filtered_results)} installations for platform "
            f"{platform_type_value}"
        )

    def test_installation_error_handling(self) -> None:
        """Test error handling for invalid UUID."""
        # Test with invalid UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endorlabs.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            installation.get_installation(self.client, self.tenant_root, "invalid-uuid")
        assert exc_info.value.resource_uuid == "invalid-uuid"
        assert exc_info.value.operation == "get"
        assert exc_info.value.status_code == 400
