"""
Test cases for Finding resource operations.

Tests GET and PATCH operations for Finding resources, including tag management.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import finding


@pytest.mark.integration
class TestFinding:
    """Test cases for Finding resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self):
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.tgowan-endor")

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

    @pytest.fixture
    def sample_finding(self):
        """Fetch minimal sample data (1 item) for UUID operations.
        
        Function-scoped but only fetches when explicitly requested by tests.
        Only fetches 1 item without traverse for fast setup. Tests that need
        sample data should request this fixture explicitly.
        """
        from endor_cockpit.types import ListParameters

        # Fetch 1 item without traverse (fast)
        results = finding.list_findings(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=1),
            max_pages=1,
        )
        if not results:
            pytest.skip("No findings available for testing")
        return results[0]  # Return single item, not list

    def test_finding_get_list(self):
        """Test GET findings operation."""
        print("\n=== TESTING GET FINDINGS ===")

        # Test list_findings with pagination limits
        import conftest

        from endor_cockpit.types import ListParameters

        findings_list = finding.list_findings(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(findings_list, list), "Should return a list of findings"
        assert len(findings_list) > 0, "Should have at least one finding"

        print(f"Found {len(findings_list)} findings")

        # Display first few findings
        for _i, finding_item in enumerate(findings_list[:10]):  # Show first 10
            print(f"Finding {finding_item.uuid}: {finding_item.meta.name}")
            if finding_item.meta.tags:
                print(f"  Finding meta tags: {finding_item.meta.tags}")
            if finding_item.spec.finding_tags:
                print(f"  Finding spec finding_tags: {finding_item.spec.finding_tags}")

    def test_finding_get_by_uuid(self, sample_finding):
        """Test GET finding by UUID operation."""
        print("\n=== TESTING GET FINDING BY UUID ===")

        finding_item = sample_finding
        # Use the finding's actual namespace
        finding_namespace = (
            finding_item.tenant_meta.namespace
            if finding_item.tenant_meta
            else self.namespace
        )
        retrieved_finding = finding.get_finding(
            self.client, finding_namespace, finding_item.uuid
        )

        assert retrieved_finding is not None, (
            "Should successfully retrieve finding by UUID"
        )
        assert retrieved_finding.uuid == finding_item.uuid, (
            "Retrieved finding should match original"
        )
        assert retrieved_finding.meta.name == finding_item.meta.name, (
            "Finding name should match"
        )

        print(f"Successfully retrieved finding: {retrieved_finding.uuid}")
        print(f"Finding name: {retrieved_finding.meta.name}")
        if retrieved_finding.meta.tags:
            print(f"Finding meta tags: {retrieved_finding.meta.tags}")
        if retrieved_finding.spec.finding_tags:
            print(f"Finding spec finding_tags: {retrieved_finding.spec.finding_tags}")


if __name__ == "__main__":
    # Run tests directly
    import os
    import sys

    # Set up environment
    # Require ENDOR_NAMESPACE to be set
    if not os.getenv("ENDOR_NAMESPACE"):
        print("ERROR: ENDOR_NAMESPACE environment variable must be set")
        sys.exit(1)

    # Create test instance and manually set up
    test_instance = TestFinding()

    # Manual setup
    import conftest

    from endor_cockpit.types import ListParameters

    test_instance.client = APIClient(auth_method="api-key")
    test_instance.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.tgowan-endor")
    test_instance.findings = finding.list_findings(
        test_instance.client,
        test_instance.namespace,
        list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
        max_pages=conftest.TEST_MAX_PAGES,
    )

    try:
        print("Running finding resource tests...")

        # Run all tests
        test_instance.test_finding_get_list()
        test_instance.test_finding_get_by_uuid()
        test_instance.test_finding_patch_tags()
        test_instance.test_finding_structure_analysis()
        test_instance.test_finding_spec_tag_limitation()
        test_instance.test_finding_operations_summary()

        print("\n[SUCCESS] All finding tests completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
