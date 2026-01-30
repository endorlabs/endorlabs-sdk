"""Test cases for Installation resource operations.

Tests GET operations for Installation resources.
Installations are read-only resources managed by platform integrations.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import installation
from endor_cockpit.types import ListParameters


@pytest.mark.integration
class TestInstallation:
    """Test cases for Installation resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self) -> None:
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        import conftest

        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Tenant root: list installations from root then traverse (tenant-wide).
        self.tenant_root = self.namespace.split(".")[0]

    @pytest.fixture
    def sample_installation(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Uses traverse=True to search across all namespaces, matching the
        pattern used in test_installation_list.
        """
        # Fetch 1 item with traverse to find installations across namespaces
        results = installation.list_installations(
            self.client,
            self.tenant_root,
            list_params=ListParameters(traverse=True, page_size=1),
            max_pages=1,
        )
        if not results:
            pytest.skip("No installations available for testing")
        return results[0]  # Return single item, not list

    def test_installation_list(self) -> None:
        """Test LIST installations operation."""
        print("\n=== TESTING LIST INSTALLATIONS ===")

        # Test list_installations with traverse
        import conftest

        installations_list = installation.list_installations(
            self.client,
            self.tenant_root,
            list_params=ListParameters(
                traverse=True,
                page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
            ),
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(installations_list, list), (
            "Should return a list of installations"
        )
        assert len(installations_list) > 0, (
            f"Should have at least one installation "
            f"(namespace: {self.tenant_root}, "
            f"traverse: True, found: {len(installations_list)})"
        )

        print(f"Found {len(installations_list)} installations")

        # Display first few installations
        for _i, installation_item in enumerate(installations_list[:5]):
            print(
                f"Installation {installation_item.uuid}: "
                f"{installation_item.meta.name if installation_item.meta else 'N/A'}"
            )
            if installation_item.spec:
                if installation_item.spec.platform_type:
                    print(f"  Platform: {installation_item.spec.platform_type}")
                if installation_item.spec.external_name:
                    print(f"  External name: {installation_item.spec.external_name}")
                if installation_item.spec.target_type:
                    print(f"  Target type: {installation_item.spec.target_type}")
                if installation_item.spec.suspended is not None:
                    print(f"  Suspended: {installation_item.spec.suspended}")

    def test_installation_get_by_uuid(self, sample_installation) -> None:
        """Test GET installation by UUID operation."""
        print("\n=== TESTING GET INSTALLATION BY UUID ===")

        installation_item = sample_installation
        # Use the installation's actual namespace
        # (may be in child namespace when traverse=True)
        installation_namespace = (
            installation_item.tenant_meta.namespace
            if installation_item.tenant_meta
            else self.tenant_root
        )
        retrieved_installation = installation.get_installation(
            self.client, installation_namespace, installation_item.uuid
        )

        assert retrieved_installation is not None, (
            "Should successfully retrieve installation by UUID"
        )
        assert retrieved_installation.uuid == installation_item.uuid, (
            "Retrieved installation should match original"
        )
        if retrieved_installation.meta and installation_item.meta:
            assert retrieved_installation.meta.name == installation_item.meta.name, (
                "Installation name should match"
            )

        print(f"Successfully retrieved installation: {retrieved_installation.uuid}")
        if retrieved_installation.meta:
            print(f"Installation name: {retrieved_installation.meta.name}")
        if retrieved_installation.spec:
            if retrieved_installation.spec.platform_type:
                print(f"Platform: {retrieved_installation.spec.platform_type}")
            if retrieved_installation.spec.external_name:
                print(f"External name: {retrieved_installation.spec.external_name}")

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
            pytest.skip("No installations for platform in this environment")

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

    def test_installation_with_traverse(self) -> None:
        """Test listing installations with traverse (child namespaces)."""
        print("\n=== TESTING LIST INSTALLATIONS WITH TRAVERSE ===")

        # List with traverse enabled
        import conftest

        list_params = ListParameters(
            traverse=True,
            page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
        )

        installations_list = installation.list_installations(
            self.client,
            self.tenant_root,
            list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        assert isinstance(installations_list, list), (
            "Should return a list of installations"
        )
        print(f"Found {len(installations_list)} installations (with traverse)")

    def test_installation_pagination(self) -> None:
        """Test pagination capabilities."""
        # Test with page size
        import conftest

        paginated_results = installation.list_installations(
            self.client,
            self.tenant_root,
            list_params=ListParameters(page_size=5, traverse=True),
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(paginated_results, list)
        assert len(paginated_results) > 0, (
            f"Should have at least one installation "
            f"(namespace: {self.tenant_root}, "
            f"traverse: True, found: {len(paginated_results)})"
        )

    def test_installation_error_handling(self) -> None:
        """Test error handling for invalid UUID."""
        # Test with invalid UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endor_cockpit.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            installation.get_installation(self.client, self.tenant_root, "invalid-uuid")
        assert exc_info.value.resource_uuid == "invalid-uuid"
        assert exc_info.value.operation == "get"
        assert exc_info.value.status_code == 400
