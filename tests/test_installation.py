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
    def setup(self):
        """Set up test environment."""
        self.client = APIClient()
        self.namespace = os.getenv("ENDOR_NAMESPACE", "")

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Get test data - use parent namespace to access child resources
        parts = self.namespace.split(".")
        self.parent_namespace = parts[0] if len(parts) > 1 else self.namespace

        # List installations from parent namespace to get available data
        import conftest

        self.installations = installation.list_installations(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(
                page_size=conftest.TEST_PAGE_SIZE,
                include_child_namespaces=True,
            ),
        )
        if not self.installations:
            pytest.skip("No installations available for testing")

    def test_installation_list(self):
        """Test LIST installations operation."""
        print("\n=== TESTING LIST INSTALLATIONS ===")

        # Test list_installations with traverse
        installations_list = installation.list_installations(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(include_child_namespaces=True),
        )
        assert isinstance(installations_list, list), (
            "Should return a list of installations"
        )
        assert len(installations_list) > 0, "Should have at least one installation"

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

    def test_installation_get_by_uuid(self):
        """Test GET installation by UUID operation."""
        print("\n=== TESTING GET INSTALLATION BY UUID ===")

        installation_item = self.installations[0]
        retrieved_installation = installation.get_installation(
            self.client, self.parent_namespace, installation_item.uuid
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
                print(
                    f"External name: {retrieved_installation.spec.external_name}"
                )

    def test_installation_filter_by_platform(self):
        """Test filtering installations by platform type."""
        print("\n=== TESTING FILTER INSTALLATIONS BY PLATFORM ===")

        # Get first installation to extract platform type
        if not self.installations:
            pytest.skip("No installations available for filtering test")

        first_installation = self.installations[0]
        if not first_installation.spec or not first_installation.spec.platform_type:
            pytest.skip("Installation has no platform_type")

        platform_type = first_installation.spec.platform_type

        # Filter installations by platform
        list_params = ListParameters(
            filter=f'spec.platform_type=="{platform_type}"',
            include_child_namespaces=True,
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
        list_params = ListParameters(
            include_child_namespaces=True,
        )

        installations_list = installation.list_installations(
            self.client, self.parent_namespace, list_params
        )

        assert isinstance(installations_list, list), (
            "Should return a list of installations"
        )
        print(f"Found {len(installations_list)} installations (with traverse)")

    def test_installation_field_validation(self):
        """Test field validation and required fields."""
        installation_item = self.installations[0]

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
        paginated_results = installation.list_installations(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(
                page_size=5, include_child_namespaces=True
            ),
        )
        assert isinstance(paginated_results, list)
        assert len(paginated_results) > 0

    def test_installation_error_handling(self):
        """Test error handling for invalid UUID."""
        # Test with invalid UUID
        invalid_installation = installation.get_installation(
            self.client, self.parent_namespace, "invalid-uuid"
        )
        assert invalid_installation is None

    def test_installation_platform_distribution(self):
        """Test and analyze installation platform distribution."""
        installations_list = installation.list_installations(
            self.client, self.parent_namespace
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
                    str(inst.spec.target_type)
                    if inst.spec.target_type
                    else "Unknown"
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

        assert len(installations_list) > 0

