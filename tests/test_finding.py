"""Test cases for Finding resource operations.

Tests GET and PATCH operations for Finding resources, including tag management.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import conftest

from endorlabs.resources import finding
from endorlabs.resources.finding import (
    Finding,
    FindingMetaUpdate,
    FindingSpec,
    UpdateFindingPayload,
)


class TestFindingGreenfieldAlias:
    """Unit tests: greenfield attribute names (context) and serialization.

    These tests assert .context and model_dump(by_alias=True)["context"] so that
    after renaming finding_context -> context, they pass without change.
    """

    def test_finding_context_attribute_and_serialization(self) -> None:
        """Finding exposes .context and serializes with key 'context'."""
        payload = {
            "uuid": "test-uuid",
            "meta": {"name": "test-finding"},
            "spec": {},
            "tenant_meta": {"namespace": "test-ns"},
            "context": {"id": "c1", "type": "scan"},
        }
        finding = Finding(**payload)
        assert finding.context is not None
        assert getattr(finding.context, "id", None) == "c1"
        dumped = finding.model_dump(by_alias=True)
        assert "context" in dumped
        assert dumped["context"] is not None


@pytest.mark.integration
class TestFinding:
    """Test cases for Finding resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace, root_namespace) -> None:
        """Fast setup: client and namespace from conftest."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.tenant_root = root_namespace
        self.created_finding_uuids = []

    def teardown_method(self) -> None:
        """Clean up any resources created during tests."""
        # Findings are read-only; cleanup is a no-op for consistent structure.
        if hasattr(self, "created_finding_uuids"):
            self.created_finding_uuids.clear()

    def test_finding_list(self) -> None:
        """LIST from tenant root with traverse (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        result = client.finding.list(
            traverse=True,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_finding_get(self) -> None:
        """GET first item from LIST (root + traverse) (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.finding.list(
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
        got = client.finding.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    @pytest.fixture
    def sample_finding(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Only fetches 1 item without traverse for fast setup. Tests that need
        sample data should request this fixture explicitly.
        """
        from endorlabs.exceptions import NotFoundError, ServerError
        from endorlabs.types import ListParameters

        try:
            results = finding.list_findings(
                self.client,
                self.namespace,
                list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
                max_pages=conftest.TEST_MAX_PAGES,
            )
        except NotFoundError:
            pytest.skip(
                "List returned 404 (resource does not exist to user: "
                "namespace not accessible to credential or resource no longer exists)"
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    def test_finding_list_by_sca(self) -> None:
        """Test filtering findings by SCA category."""
        print("\n=== TESTING FILTER FINDINGS BY SCA ===")
        import conftest

        from endorlabs.types import ListParameters

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

        from endorlabs.types import ListParameters

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

        from endorlabs.types import ListParameters

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

        from endorlabs.types import ListParameters

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

        from endorlabs.types import ListParameters

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

        from endorlabs.types import ListParameters

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

        from endorlabs.types import ListParameters

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

    @pytest.mark.writes
    def test_finding_update_with_mask(self, sample_finding) -> None:
        """Test UPDATE finding operation with update_mask parameter.

        Local-only: updating findings requires elevated permissions (403 in CI).
        """
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
        from endorlabs.resources.finding import FindingTags

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

    @pytest.mark.writes
    def test_client_ux_update_finding(self) -> None:
        """Consumer UX: client.finding.get() then update then revert."""
        import endorlabs
        from endorlabs.resources.finding import FindingTags

        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        findings = client.finding.list(max_pages=conftest.TEST_MAX_PAGES)
        if not findings:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = findings[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.namespace
        )
        current = client.finding.get(item.uuid, namespace=ns)
        if not current:
            pytest.skip(f"Could not retrieve finding {item.uuid}")
        original_tags = current.meta.tags or []
        original_finding_tags = list(current.spec.finding_tags or [])
        new_tags = [*original_tags, "client-ux-update"]
        new_finding_tags = list(original_finding_tags)
        if FindingTags.UNDER_REVIEW.value not in new_finding_tags:
            new_finding_tags.append(FindingTags.UNDER_REVIEW.value)
        update_payload = UpdateFindingPayload(
            meta=FindingMetaUpdate(tags=new_tags),
            spec=FindingSpec(finding_tags=new_finding_tags),
        )
        try:
            updated = client.finding.update(
                item.uuid,
                update_payload,
                update_mask="meta.tags,spec.finding_tags",
                namespace=ns,
            )
        except Exception as e:
            pytest.skip(f"Finding update not allowed in this environment: {e}")
        assert updated is not None
        restore_payload = UpdateFindingPayload(
            meta=FindingMetaUpdate(tags=original_tags),
            spec=FindingSpec(finding_tags=original_finding_tags),
        )
        try:
            client.finding.update(
                item.uuid,
                restore_payload,
                update_mask="meta.tags,spec.finding_tags",
                namespace=ns,
            )
        except Exception as e:
            print(f"[WARNING] Failed to restore original finding values: {e}")


if __name__ == "__main__":
    # Run tests directly
    import os
    import sys

    # Set up environment
    # Require ENDOR_NAMESPACE to be set
    if not os.getenv("ENDOR_NAMESPACE"):
        print("ERROR: ENDOR_NAMESPACE environment variable must be set")
        sys.exit(1)

    try:
        print("Running finding resource tests...")
        exit_code = pytest.main([__file__, "-v", "-s"])
        if exit_code != 0:
            sys.exit(exit_code)
        print("\n[SUCCESS] All finding tests completed successfully!")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
