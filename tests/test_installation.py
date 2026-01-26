"""
Test cases for Installation resource operations.

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
    def setup_fast(self):
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.tgowan-endor")

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Get test data - use parent namespace to access child resources
        parts = self.namespace.split(".")
        self.parent_namespace = parts[0] if len(parts) > 1 else self.namespace

    @pytest.fixture
    def sample_installation(self):
        """Fetch minimal sample data (1 item) for UUID operations.
        
        Function-scoped but only fetches when explicitly requested by tests.
        Only fetches 1 item without traverse for fast setup. Tests that need
        sample data should request this fixture explicitly.
        """
        # Fetch 1 item without traverse (fast)
        results = installation.list_installations(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=1),
            max_pages=1,
        )
        if not results:
            pytest.skip("No installations available for testing")
        return results[0]  # Return single item, not list

    def test_installation_list(self):
        """Test LIST installations operation."""
        print("\n=== TESTING LIST INSTALLATIONS ===")

        # Test list_installations with traverse
        import conftest

        installations_list = installation.list_installations(
            self.client,
            self.parent_namespace,
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
            f"(namespace: {self.parent_namespace}, "
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

    def test_installation_get_by_uuid(self, sample_installation):
        """Test GET installation by UUID operation."""
        print("\n=== TESTING GET INSTALLATION BY UUID ===")

        installation_item = sample_installation
        # Use the installation's actual namespace
        # (may be in child namespace when traverse=True)
        installation_namespace = (
            installation_item.tenant_meta.namespace
            if installation_item.tenant_meta
            else self.parent_namespace
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

    def test_installation_filter_by_platform(self, sample_installation):
        """Test filtering installations by platform type."""
        print("\n=== TESTING FILTER INSTALLATIONS BY PLATFORM ===")

        # Get first installation to extract platform type
        first_installation = sample_installation
        if not first_installation.spec or not first_installation.spec.platform_type:
            pytest.skip("Installation has no platform_type")

        platform_type = first_installation.spec.platform_type

        # Filter installations by platform
        list_params = ListParameters(
            filter=f'spec.platform_type=="{platform_type}"',
            traverse=True,
        )

        filtered_results = installation.list_installations(
            self.client, self.parent_namespace, list_params
        )

        assert isinstance(filtered_results, list), (
            "Should return a list of filtered installations"
        )
        assert len(filtered_results) > 0, (
            "Should have at least one installation for the platform"
        )

        # Verify all results have the same platform
        for result in filtered_results:
            if result.spec and result.spec.platform_type:
                assert result.spec.platform_type == platform_type, (
                    "All filtered results should have the same platform"
                )

        print(
            f"Found {len(filtered_results)} installations for platform {platform_type}"
        )

    def test_installation_with_traverse(self):
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
            self.parent_namespace,
            list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        assert isinstance(installations_list, list), (
            "Should return a list of installations"
        )
        print(f"Found {len(installations_list)} installations (with traverse)")

    def test_installation_field_validation(self, sample_installation):
        """Test field validation and required fields."""
        installation_item = sample_installation

        # Verify required fields are present
        assert installation_item.uuid is not None
        assert installation_item.meta is not None
        assert installation_item.meta.name is not None
        assert installation_item.spec is not None

        # Note: Many spec fields may be None as installations are
        # auto-discovered and may have incomplete data

    def test_installation_pagination(self):
        """Test pagination capabilities."""
        # Test with page size
        import conftest

        paginated_results = installation.list_installations(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=5, traverse=True),
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(paginated_results, list)
        assert len(paginated_results) > 0, (
            f"Should have at least one installation "
            f"(namespace: {self.parent_namespace}, "
            f"traverse: True, found: {len(paginated_results)})"
        )

    def test_installation_error_handling(self):
        """Test error handling for invalid UUID."""
        # Test with invalid UUID
        invalid_installation = installation.get_installation(
            self.client, self.parent_namespace, "invalid-uuid"
        )
        assert invalid_installation is None

    def test_installation_platform_distribution(self):
        """Test and analyze installation platform distribution."""
        import conftest

        installations_list = installation.list_installations(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(
                page_size=conftest.TEST_PAGE_SIZE,
                traverse=True,
            ),
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        platform_counts = {}
        target_type_counts = {}
        suspended_counts = {"suspended": 0, "active": 0}

        for inst in installations_list:
            if inst.spec:
                platform = (
                    str(inst.spec.platform_type)
                    if inst.spec.platform_type
                    else "Unknown"
                )
                platform_counts[platform] = platform_counts.get(platform, 0) + 1

                target_type = (
                    str(inst.spec.target_type) if inst.spec.target_type else "Unknown"
                )
                target_type_counts[target_type] = (
                    target_type_counts.get(target_type, 0) + 1
                )

                if inst.spec.suspended:
                    suspended_counts["suspended"] += 1
                else:
                    suspended_counts["active"] += 1

        print("\n=== Installation Distribution ===")
        print("Platform distribution:")
        for platform, count in platform_counts.items():
            print(f"  {platform}: {count}")

        print("Target type distribution:")
        for target_type, count in target_type_counts.items():
            print(f"  {target_type}: {count}")

        print("Suspended status:")
        for status, count in suspended_counts.items():
            print(f"  {status}: {count}")

        assert len(installations_list) > 0, (
            f"Should have at least one installation "
            f"(namespace: {self.parent_namespace}, "
            f"traverse: True, found: {len(installations_list)})"
        )
