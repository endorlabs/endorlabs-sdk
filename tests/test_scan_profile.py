"""
Test cases for ScanProfile resource operations.

Tests CRUD operations for ScanProfile resources. ScanProfiles define scan
configuration including toolchains and scan parameters.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import scan_profile
from endor_cockpit.resources.scan_profile import (
    AISastAnalysisMode,
    AISastAnalysisParameters,
    AutomatedScanParameters,
    CreateScanProfilePayload,
    ExporterParameters,
    RemediationParameters,
    ScanProfileMetaCreate,
    ScanProfileSpecCreate,
    SecurityReviewScannerParameters,
    UpdateScanProfilePayload,
)
from endor_cockpit.types import ListParameters


@pytest.mark.integration
class TestScanProfile:
    """Test cases for ScanProfile resource operations."""

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

        # List scan profiles from parent namespace to get available data
        import conftest

        self.scan_profiles = scan_profile.list_scan_profiles(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
        )

    def test_scan_profile_list(self):
        """Test LIST scan profiles operation."""
        print("\n=== TESTING LIST SCAN PROFILES ===")

        # Test list_scan_profiles
        scan_profiles_list = scan_profile.list_scan_profiles(
            self.client, self.parent_namespace
        )
        assert isinstance(scan_profiles_list, list), (
            "Should return a list of scan profiles"
        )

        print(f"Found {len(scan_profiles_list)} scan profiles")

        # Display first few scan profiles
        for _i, profile in enumerate(scan_profiles_list[:5]):  # Show first 5
            print(
                f"ScanProfile {profile.uuid}: "
                f"{profile.meta.name if profile.meta else 'N/A'}"
            )
            if profile.spec:
                if profile.spec.is_default:
                    print("  Default: Yes")
                if profile.propagate:
                    print("  Propagate: Yes")

    def test_scan_profile_get_by_uuid(self):
        """Test GET scan profile by UUID operation."""
        print("\n=== TESTING GET SCAN PROFILE BY UUID ===")

        if not self.scan_profiles:
            pytest.skip("No scan profiles available for testing")

        profile = self.scan_profiles[0]
        retrieved_profile = scan_profile.get_scan_profile(
            self.client, self.parent_namespace, profile.uuid
        )

        assert retrieved_profile is not None, (
            "Should successfully retrieve scan profile by UUID"
        )
        assert retrieved_profile.uuid == profile.uuid, (
            "Retrieved scan profile should match original"
        )
        if retrieved_profile.meta and profile.meta:
            assert retrieved_profile.meta.name == profile.meta.name, (
                "Scan profile name should match"
            )

        print(f"Successfully retrieved scan profile: {retrieved_profile.uuid}")
        if retrieved_profile.meta:
            print(f"Scan profile name: {retrieved_profile.meta.name}")

    def test_scan_profile_field_validation(self):
        """Test field validation and required fields."""
        if not self.scan_profiles:
            pytest.skip("No scan profiles available for testing")

        profile = self.scan_profiles[0]

        # Verify required fields are present
        assert profile.uuid is not None
        assert profile.meta is not None
        assert profile.meta.name is not None
        assert profile.spec is not None

    def test_scan_profile_with_traverse(self):
        """Test listing scan profiles with traverse (child namespaces)."""
        print("\n=== TESTING LIST SCAN PROFILES WITH TRAVERSE ===")

        # List with traverse enabled
        list_params = ListParameters(traverse=True)

        scan_profiles_list = scan_profile.list_scan_profiles(
            self.client, self.parent_namespace, list_params
        )

        assert isinstance(scan_profiles_list, list), (
            "Should return a list of scan profiles"
        )
        print(f"Found {len(scan_profiles_list)} scan profiles (with traverse)")

    def test_scan_profile_pagination(self):
        """Test pagination capabilities."""
        # Test with page size
        paginated_profiles = scan_profile.list_scan_profiles(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=5),
        )
        assert isinstance(paginated_profiles, list)

    def test_scan_profile_error_handling(self):
        """Test error handling for invalid UUID."""
        # Test with invalid UUID
        invalid_profile = scan_profile.get_scan_profile(
            self.client, self.parent_namespace, "invalid-uuid"
        )
        assert invalid_profile is None

    def test_scan_profile_structure_analysis(self):
        """Test and analyze scan profile structure."""
        if not self.scan_profiles:
            pytest.skip("No scan profiles available for testing")

        print("\n=== Scan Profile Structure Analysis ===")
        default_count = 0
        propagate_count = 0
        has_automated_params = 0
        has_toolchain = 0

        for profile in self.scan_profiles:
            if profile.spec:
                if profile.spec.is_default:
                    default_count += 1
                if profile.spec.automated_scan_parameters:
                    has_automated_params += 1
                if profile.spec.toolchain_profile:
                    has_toolchain += 1
            if profile.propagate:
                propagate_count += 1

        print(f"Total profiles: {len(self.scan_profiles)}")
        print(f"Default profiles: {default_count}")
        print(f"Propagated profiles: {propagate_count}")
        print(f"Profiles with automated params: {has_automated_params}")
        print(f"Profiles with toolchain: {has_toolchain}")

        assert len(self.scan_profiles) > 0

