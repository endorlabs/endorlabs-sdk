"""Test cases for Finding resource operations.

Tests GET and PATCH operations for Finding resources, including tag management.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import conftest

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import finding
from endor_cockpit.resources.finding import (
    FindingMetaUpdate,
    FindingSpec,
    UpdateFindingPayload,
)


@pytest.mark.integration
class TestFinding:
    """Test cases for Finding resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self) -> None:
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Extract tenant root namespace for traverse operations
        # Tenant root is the first part before the first dot
        self.tenant_root = self.namespace.split(".")[0]

        # Track created resources for cleanup
        # (findings are read-only, but establish pattern)
        self.created_finding_uuids = []

    def teardown_method(self) -> None:
        """Clean up any resources created during tests."""
        # Findings are read-only and cannot be deleted, but we establish the pattern
        # for consistency and future use if findings become deletable
        if hasattr(self, "created_finding_uuids"):
            # Note: Findings cannot be deleted via API, so cleanup is a no-op
            # This method exists to maintain consistent test structure
            self.created_finding_uuids.clear()

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

    def test_finding_get_list(self) -> None:
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

    def test_finding_get_by_uuid(self, sample_finding) -> None:
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

    def test_finding_list_by_sca(self) -> None:
        """Test filtering findings by SCA category."""
        print("\n=== TESTING FILTER FINDINGS BY SCA ===")
        import conftest

        from endor_cockpit.types import ListParameters

        list_params = ListParameters(
            filter="spec.finding_categories contains [FINDING_CATEGORY_SCA]",
            page_size=conftest.TEST_PAGE_SIZE,
            traverse=True,
        )

        findings = finding.list_findings(
            self.client,
            self.tenant_root,
            list_params=list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        assert isinstance(findings, list), "Should return a list of findings"
        print(f"Found {len(findings)} SCA findings")

        # Validate all returned findings have SCA category
        for f in findings:
            if f.spec.finding_categories:
                assert "FINDING_CATEGORY_SCA" in f.spec.finding_categories or any(
                    "SCA" in str(cat) for cat in f.spec.finding_categories
                ), (
                    f"Finding {f.uuid} should have SCA category, "
                    f"got {f.spec.finding_categories}"
                )

        if findings:
            print(f"Sample SCA finding: {findings[0].uuid} - {findings[0].meta.name}")

    def test_finding_list_by_sast(self) -> None:
        """Test filtering findings by SAST category."""
        print("\n=== TESTING FILTER FINDINGS BY SAST ===")
        import conftest

        from endor_cockpit.types import ListParameters

        list_params = ListParameters(
            filter="spec.finding_categories contains [FINDING_CATEGORY_SAST]",
            page_size=conftest.TEST_PAGE_SIZE,
            traverse=True,
        )

        findings = finding.list_findings(
            self.client,
            self.tenant_root,
            list_params=list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        assert isinstance(findings, list), "Should return a list of findings"
        print(f"Found {len(findings)} SAST findings")

        # Validate all returned findings have SAST category
        for f in findings:
            if f.spec.finding_categories:
                assert "FINDING_CATEGORY_SAST" in f.spec.finding_categories or any(
                    "SAST" in str(cat) for cat in f.spec.finding_categories
                ), (
                    f"Finding {f.uuid} should have SAST category, "
                    f"got {f.spec.finding_categories}"
                )

        if findings:
            print(f"Sample SAST finding: {findings[0].uuid} - {findings[0].meta.name}")

    def test_finding_list_by_secrets(self) -> None:
        """Test filtering findings by Secrets category."""
        print("\n=== TESTING FILTER FINDINGS BY SECRETS ===")
        import conftest

        from endor_cockpit.types import ListParameters

        list_params = ListParameters(
            filter="spec.finding_categories contains [FINDING_CATEGORY_SECRETS]",
            page_size=conftest.TEST_PAGE_SIZE,
            traverse=True,
        )

        findings = finding.list_findings(
            self.client,
            self.tenant_root,
            list_params=list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        assert isinstance(findings, list), "Should return a list of findings"
        print(f"Found {len(findings)} Secrets findings")

        # Validate all returned findings have Secrets category
        for f in findings:
            if f.spec.finding_categories:
                assert "FINDING_CATEGORY_SECRETS" in f.spec.finding_categories or any(
                    "SECRETS" in str(cat) for cat in f.spec.finding_categories
                ), (
                    f"Finding {f.uuid} should have Secrets category, "
                    f"got {f.spec.finding_categories}"
                )

        if findings:
            print(
                f"Sample Secrets finding: {findings[0].uuid} - {findings[0].meta.name}"
            )

    def test_finding_list_by_container(self) -> None:
        """Test filtering findings by Container category."""
        print("\n=== TESTING FILTER FINDINGS BY CONTAINER ===")
        import conftest

        from endor_cockpit.types import ListParameters

        list_params = ListParameters(
            filter="spec.finding_categories contains [FINDING_CATEGORY_CONTAINER]",
            page_size=conftest.TEST_PAGE_SIZE,
        )

        findings = finding.list_findings(
            self.client,
            self.tenant_root,
            list_params=list_params,
            max_pages=conftest.TEST_MAX_PAGES,
        )

        assert isinstance(findings, list), "Should return a list of findings"
        print(f"Found {len(findings)} Container findings")

        # Validate all returned findings have Container category (if any exist)
        for f in findings:
            if f.spec.finding_categories:
                assert "FINDING_CATEGORY_CONTAINER" in f.spec.finding_categories or any(
                    "CONTAINER" in str(cat) for cat in f.spec.finding_categories
                ), (
                    f"Finding {f.uuid} should have Container category, "
                    f"got {f.spec.finding_categories}"
                )

        if findings:
            print(
                f"Sample Container finding: {findings[0].uuid} - "
                f"{findings[0].meta.name}"
            )
        else:
            print("No Container findings found (may not exist in platform yet)")

    def test_finding_list_by_ai_models(self) -> None:
        """Test filtering findings by AI Models category."""
        print("\n=== TESTING FILTER FINDINGS BY AI MODELS ===")
        import conftest

        from endor_cockpit.types import ListParameters

        list_params = ListParameters(
            filter="spec.finding_categories contains [FINDING_CATEGORY_AI_MODELS]",
            page_size=conftest.TEST_PAGE_SIZE,
            traverse=True,
        )

        findings = finding.list_findings(
            self.client,
            self.tenant_root,
            list_params=list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        assert isinstance(findings, list), "Should return a list of findings"
        print(f"Found {len(findings)} AI Models findings")

        # Validate all returned findings have AI Models category
        for f in findings:
            if f.spec.finding_categories:
                assert "FINDING_CATEGORY_AI_MODELS" in f.spec.finding_categories or any(
                    "AI_MODELS" in str(cat) for cat in f.spec.finding_categories
                ), (
                    f"Finding {f.uuid} should have AI Models category, "
                    f"got {f.spec.finding_categories}"
                )

        if findings:
            print(
                f"Sample AI Models finding: {findings[0].uuid} - "
                f"{findings[0].meta.name}"
            )
        else:
            print("No AI Models findings found (may not exist in platform yet)")

    def test_finding_list_by_license_risk(self) -> None:
        """Test filtering findings by License Risk category."""
        print("\n=== TESTING FILTER FINDINGS BY LICENSE RISK ===")
        import conftest

        from endor_cockpit.types import ListParameters

        list_params = ListParameters(
            filter="spec.finding_categories contains [FINDING_CATEGORY_LICENSE_RISK]",
            page_size=conftest.TEST_PAGE_SIZE,
            traverse=True,
        )

        findings = finding.list_findings(
            self.client,
            self.tenant_root,
            list_params=list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        assert isinstance(findings, list), "Should return a list of findings"
        print(f"Found {len(findings)} License Risk findings")

        # Validate all returned findings have License Risk category
        for f in findings:
            if f.spec.finding_categories:
                assert (
                    "FINDING_CATEGORY_LICENSE_RISK" in f.spec.finding_categories
                    or any(
                        "LICENSE_RISK" in str(cat) for cat in f.spec.finding_categories
                    )
                ), (
                    f"Finding {f.uuid} should have License Risk category, "
                    f"got {f.spec.finding_categories}"
                )

        if findings:
            print(
                f"Sample License Risk finding: {findings[0].uuid} - "
                f"{findings[0].meta.name}"
            )
        else:
            print("No License Risk findings found (may not exist in platform yet)")

    def test_finding_list_by_scpm(self) -> None:
        """Test filtering findings by SCPM (RSPM) category."""
        print("\n=== TESTING FILTER FINDINGS BY SCPM (RSPM) ===")
        import conftest

        from endor_cockpit.types import ListParameters

        list_params = ListParameters(
            filter="spec.finding_categories contains [FINDING_CATEGORY_SCPM]",
            page_size=conftest.TEST_PAGE_SIZE,
            traverse=True,
        )

        findings = finding.list_findings(
            self.client,
            self.tenant_root,
            list_params=list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        assert isinstance(findings, list), "Should return a list of findings"
        print(f"Found {len(findings)} SCPM (RSPM) findings")

        # Validate all returned findings have SCPM category
        for f in findings:
            if f.spec.finding_categories:
                assert "FINDING_CATEGORY_SCPM" in f.spec.finding_categories or any(
                    "SCPM" in str(cat) for cat in f.spec.finding_categories
                ), (
                    f"Finding {f.uuid} should have SCPM category, "
                    f"got {f.spec.finding_categories}"
                )

        if findings:
            print(f"Sample SCPM finding: {findings[0].uuid} - {findings[0].meta.name}")
        else:
            print("No SCPM findings found (may not exist in platform yet)")

    def test_finding_update_with_mask(self, sample_finding) -> None:
        """Test UPDATE finding operation with update_mask parameter."""
        print("\n=== TESTING FINDING UPDATE WITH MASK ===")

        finding_uuid = sample_finding.uuid

        # Get current finding state
        current_finding = finding.get_finding(self.client, self.namespace, finding_uuid)
        if not current_finding:
            pytest.skip(f"Could not retrieve finding {finding_uuid}")

        # Store original values
        original_tags = current_finding.meta.tags or []
        original_finding_tags = current_finding.spec.finding_tags or []

        # Create update payload - only update safe fields
        # Note: dismiss field is managed automatically by API and cannot be set directly
        # Use set to avoid duplicates if test runs multiple times
        new_tags = list(set([*original_tags, "test-update", "mask-test"]))
        # Use valid FindingTags enum values
        # (API may require enum values, not arbitrary strings)
        # UNDER_REVIEW is a valid enum value that can be used for testing
        from endor_cockpit.resources.finding import FindingTags

        new_finding_tags = list(
            set(
                (original_finding_tags or [])
                + [FindingTags.UNDER_REVIEW.value, FindingTags.TEST.value]
            )
        )

        update_payload = UpdateFindingPayload(
            meta=FindingMetaUpdate(tags=new_tags),
            spec=FindingSpec(
                finding_tags=new_finding_tags,
                # Don't set dismiss - API manages it automatically
            ),
        )

        print(f"Updating finding: {finding_uuid}")
        print(f"New tags: {new_tags}")
        print(f"New finding_tags: {new_finding_tags}")

        # Update the finding with update_mask (exclude spec.dismiss - API manages it)
        updated_finding = finding.update_finding(
            self.client,
            self.namespace,
            finding_uuid,
            update_payload,
            "meta.tags,spec.finding_tags",
        )

        assert updated_finding is not None, "Finding update should succeed"
        assert "test-update" in updated_finding.meta.tags, (
            "Updated tag should be present"
        )
        assert "mask-test" in updated_finding.meta.tags, "Updated tag should be present"
        # Check for valid enum values (API may normalize to enum values)
        finding_tags_values = updated_finding.spec.finding_tags or []
        assert (
            FindingTags.UNDER_REVIEW.value in finding_tags_values
            or FindingTags.UNDER_REVIEW.value.replace("FINDING_TAGS_", "")
            in [tag.replace("FINDING_TAGS_", "") for tag in finding_tags_values]
        ), "Updated finding tag UNDER_REVIEW should be present"
        assert (
            FindingTags.TEST.value in finding_tags_values
            or FindingTags.TEST.value.replace("FINDING_TAGS_", "")
            in [tag.replace("FINDING_TAGS_", "") for tag in finding_tags_values]
        ), "Updated finding tag TEST should be present"

        print(f"[SUCCESS] Finding updated: {updated_finding.uuid}")
        print(f"Updated tags: {updated_finding.meta.tags}")
        print(f"Updated finding_tags: {updated_finding.spec.finding_tags}")

        # Restore original values if possible
        restore_payload = UpdateFindingPayload(
            meta=FindingMetaUpdate(tags=original_tags),
            spec=FindingSpec(
                finding_tags=original_finding_tags,
                # Don't set dismiss - API manages it automatically
            ),
        )
        try:
            finding.update_finding(
                self.client,
                self.namespace,
                finding_uuid,
                restore_payload,
                "meta.tags,spec.finding_tags",
            )
            print("[CLEANUP] Restored original finding values")
        except Exception as e:
            print(f"[WARNING] Failed to restore original values: {e}")


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
    test_instance.namespace = os.getenv(
        "ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT
    )
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
