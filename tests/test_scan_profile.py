"""Test cases for ScanProfile resource operations.

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
from endor_cockpit.types import ListParameters


@pytest.mark.integration
class TestScanProfile:
    """Test cases for ScanProfile resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self) -> None:
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        import conftest

        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Track created resources for cleanup
        self.created_scan_profile_uuids = []

        # Get test data - use parent namespace to access child resources
        parts = self.namespace.split(".")
        self.parent_namespace = parts[0] if len(parts) > 1 else self.namespace

    def teardown_method(self) -> None:
        """Clean up any scan profiles created during tests."""
        if hasattr(self, "created_scan_profile_uuids"):
            for scan_profile_uuid in self.created_scan_profile_uuids:
                try:
                    scan_profile.delete_scan_profile(
                        self.client, self.parent_namespace, scan_profile_uuid
                    )
                    print(f"[CLEANUP] Deleted test scan profile: {scan_profile_uuid}")
                except Exception as e:
                    print(
                        f"[WARNING] Failed to delete test scan profile "
                        f"{scan_profile_uuid}: {e}"
                    )
            self.created_scan_profile_uuids.clear()

    @pytest.fixture
    def sample_scan_profile(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Only fetches 1 item for fast setup. Tests that need sample data should
        request this fixture explicitly.
        """
        results = scan_profile.list_scan_profiles(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=1),
            max_pages=1,
        )
        if not results:
            pytest.skip("No scan profiles available for testing")
        return results[0]  # Return single item, not list

    def test_scan_profile_list(self) -> None:
        """Test LIST scan profiles operation."""
        print("\n=== TESTING LIST SCAN PROFILES ===")

        # Test list_scan_profiles with pagination limits
        import conftest

        from endor_cockpit.types import ListParameters

        scan_profiles_list = scan_profile.list_scan_profiles(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
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

    def test_scan_profile_get_by_uuid(self, sample_scan_profile) -> None:
        """Test GET scan profile by UUID operation."""
        print("\n=== TESTING GET SCAN PROFILE BY UUID ===")

        profile = sample_scan_profile
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

    def test_scan_profile_with_traverse(self) -> None:
        """Test listing scan profiles with traverse (child namespaces)."""
        print("\n=== TESTING LIST SCAN PROFILES WITH TRAVERSE ===")

        # List with traverse enabled
        import conftest

        list_params = ListParameters(
            traverse=True,
            page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
        )

        scan_profiles_list = scan_profile.list_scan_profiles(
            self.client,
            self.parent_namespace,
            list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        assert isinstance(scan_profiles_list, list), (
            "Should return a list of scan profiles"
        )
        print(f"Found {len(scan_profiles_list)} scan profiles (with traverse)")

    def test_scan_profile_pagination(self) -> None:
        """Test pagination capabilities."""
        # Test with page size
        import conftest

        paginated_profiles = scan_profile.list_scan_profiles(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=5),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(paginated_profiles, list)

    def test_scan_profile_advanced_filtering(self) -> None:
        """Test advanced filtering capabilities."""
        print("\n=== TESTING SCAN PROFILE FILTERING ===")
        import conftest

        # Test filtering by is_default
        default_profiles = scan_profile.list_scan_profiles(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(
                filter="spec.is_default==true",
                page_size=conftest.TEST_PAGE_SIZE,
            ),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(default_profiles, list), (
            "Should return a list of scan profiles"
        )
        print(f"Found {len(default_profiles)} default scan profiles")

        # Test field masking
        masked_profiles = scan_profile.list_scan_profiles(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(
                mask="meta.name,spec.is_default",
                page_size=conftest.TEST_PAGE_SIZE,
            ),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(masked_profiles, list), (
            "Should return a list of masked scan profiles"
        )
        if masked_profiles:
            profile = masked_profiles[0]
            # Should have masked fields
            assert hasattr(profile, "meta")
            assert hasattr(profile, "spec")
            print(f"Masked profile: {profile.meta.name if profile.meta else 'N/A'}")

    def test_scan_profile_error_handling(self) -> None:
        """Test error handling for invalid UUID."""
        # Test with invalid UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endor_cockpit.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            scan_profile.get_scan_profile(
                self.client, self.parent_namespace, "invalid-uuid"
            )
        assert exc_info.value.resource_uuid == "invalid-uuid"
        assert exc_info.value.operation == "get"
        assert exc_info.value.status_code == 400
