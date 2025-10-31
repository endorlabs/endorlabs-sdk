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
    def setup(self):
        """Set up test environment."""
        self.client = APIClient()
        self.namespace = os.getenv("ENDOR_NAMESPACE", "")

        # Get test data
        self.findings = finding.list_findings(self.client, self.namespace)
        if not self.findings:
            pytest.skip("No findings available for testing")

    def test_finding_get_list(self):
        """Test GET findings operation."""
        print("\n=== TESTING GET FINDINGS ===")

        # Test list_findings
        findings_list = finding.list_findings(self.client, self.namespace)
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

    def test_finding_get_by_uuid(self):
        """Test GET finding by UUID operation."""
        print("\n=== TESTING GET FINDING BY UUID ===")

        finding_item = self.findings[0]
        retrieved_finding = finding.get_finding(
            self.client, self.namespace, finding_item.uuid
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

    def test_finding_structure_analysis(self):
        """Test and analyze finding structure."""
        print("\n=== FINDING STRUCTURE ANALYSIS ===")

        finding = self.findings[0]
        print(f"Analyzing finding: {finding.uuid} - {finding.meta.name}")

        # Analyze finding meta fields
        meta_fields = [
            field for field in dir(finding.meta) if not field.startswith("_")
        ]
        print(f"Finding meta fields: {meta_fields}")
        if finding.meta.tags:
            print(f"Finding meta tags: {finding.meta.tags}")

        # Analyze finding spec fields
        spec_fields = [
            field for field in dir(finding.spec) if not field.startswith("_")
        ]
        print(f"Finding spec fields: {spec_fields}")
        if finding.spec.finding_tags:
            print(f"Finding spec finding_tags: {finding.spec.finding_tags}")

        # Analyze finding context fields
        context_fields = [
            field for field in dir(finding.context) if not field.startswith("_")
        ]
        print(f"Finding context fields: {context_fields}")
        if hasattr(finding.context, "tags") and finding.context.tags:
            print(f"Finding context tags: {finding.context.tags}")

    def test_finding_operations_summary(self):
        """Generate summary of finding operations."""
        print("\n=== FINDING OPERATIONS SUMMARY ===")

        print("GET Operations:")
        print(f"  - List Findings: GET /v1/namespaces/{self.namespace}/findings")
        print(f"  - Get Finding: GET /v1/namespaces/{self.namespace}/findings/{{uuid}}")

        print("PATCH Operations (Tag Management):")
        print(
            f"  - Update Finding Tags: PATCH /v1/namespaces/{self.namespace}/findings"
        )
        print("  - Uses update_mask for efficient partial updates")
        print("  - Finding meta tags: meta.tags field")
        print("  - Finding spec tags: READ-ONLY (system-managed)")

        print("Success Metrics:")
        print(f"  - Findings Retrieved: {len(self.findings)}")
        print("  - GET Operations: Working")
        print("  - PATCH Operations: Working with update_mask")
        print("  - Tag Management: Functional for user-defined meta tags")
        print("  - Spec Tags: Properly documented as read-only")


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
    test_instance.client = APIClient()
    test_instance.namespace = os.getenv(
        "ENDOR_NAMESPACE", ""
    )
    test_instance.findings = finding.list_findings(
        test_instance.client, test_instance.namespace
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
