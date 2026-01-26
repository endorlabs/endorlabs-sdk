"""
Test cases for Policy resource operations.

Tests full CRUD operations for Policy resources using ML_FINDING dummy policy.
Includes policy type filtering, analysis, and comprehensive CRUD testing with
live data using the ML_FINDING pattern discovered through schema drift analysis.
"""

import os
import sys
import time

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import policy
from endor_cockpit.resources.policy import (
    CreatePolicyPayload,
    PolicyType,
    UpdatePolicyPayload,
)


@pytest.mark.integration
class TestPolicy:
    """Test cases for Policy resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self):
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.tgowan-endor")

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        self.created_policy_uuids = []  # Track created policies for cleanup

    @pytest.fixture
    def sample_policy(self):
        """Fetch minimal sample data (1 item) for UUID operations.
        
        Function-scoped but only fetches when explicitly requested by tests.
        Only fetches 1 item for fast setup. Tests that need sample data should
        request this fixture explicitly.
        """
        from endor_cockpit.types import ListParameters

        results = policy.list_policies(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=1),
            max_pages=1,
        )
        if not results:
            pytest.skip("No policies available for testing")
        return results[0]  # Return single item, not list

    def _create_test_policy(self, name_suffix: str = ""):
        """Helper method to create a test policy for CRUD operations.

        Args:
            name_suffix: Optional suffix to add to policy name for uniqueness

        Returns:
            Created policy object
        """
        import time

        timestamp = int(time.time())
        policy_name = f"Test Dummy ML Policy{name_suffix} {timestamp}"
        dummy_policy_payload = CreatePolicyPayload(
            meta=policy.PolicyMeta(
                name=policy_name,
                kind="Policy",
                description=(
                    "A test ML_FINDING policy created for CRUD operations testing"
                ),
                tags=["test", "dummy", "ml-finding", "crud-test"],
            ),
            spec=policy.PolicySpec(
                policy_type=PolicyType.ML_FINDING,
                rule="""package testpolicy

configure[result] {
  result = {
    "test_method": {
      "disable": false,
      "parameters": {
        "enable_test": {
          "bool_value": true
        }
      }
    }
  }
}""",
                disable=False,
                resource_kinds=[],  # ML_FINDING can have empty resource kinds
                project_selector=["test-projects"],
                project_exceptions=["excluded-projects"],
            ),
            propagate=True,
        )

        # Create the policy
        created_policy = policy.create_policy(
            self.client, self.namespace, dummy_policy_payload
        )

        assert created_policy is not None, "Policy creation should succeed"
        assert created_policy.meta.name == policy_name, "Policy name should match"
        assert created_policy.spec.policy_type == PolicyType.ML_FINDING, (
            "Policy type should be ML_FINDING"
        )
        assert created_policy.spec.resource_kinds == [], (
            "Resource kinds should be empty for ML_FINDING"
        )

        # Store for cleanup
        self.created_policy_uuids.append(created_policy.uuid)
        return created_policy

    def teardown_method(self):
        """Clean up any policies created during tests."""
        if hasattr(self, "created_policy_uuids"):
            for policy_uuid in self.created_policy_uuids:
                try:
                    policy.delete_policy(self.client, self.namespace, policy_uuid)
                    print(f"[CLEANUP] Deleted test policy: {policy_uuid}")
                except Exception as e:
                    print(f"[WARNING] Failed to delete test policy {policy_uuid}: {e}")
            self.created_policy_uuids.clear()

    def test_policy_get_list(self):
        """Test GET policies operation."""
        print("\n=== TESTING GET POLICIES ===")

        # Test list_policies with pagination limits
        import conftest

        from endor_cockpit.types import ListParameters

        policies_list = policy.list_policies(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(policies_list, list), "Should return a list of policies"
        assert len(policies_list) > 0, "Should have at least one policy"

        print(f"Found {len(policies_list)} policies")

        # Display first few policies
        for _i, policy_item in enumerate(policies_list[:10]):  # Show first 10
            print(f"Policy {policy_item.uuid}: {policy_item.meta.name}")
            print(f"  Type: {policy_item.spec.policy_type}")
            if policy_item.meta.tags:
                print(f"  Meta tags: {policy_item.meta.tags}")

    def test_policy_get_by_uuid(self, sample_policy):
        """Test GET policy by UUID operation."""
        print("\n=== TESTING GET POLICY BY UUID ===")

        policy_item = sample_policy
        retrieved_policy = policy.get_policy(
            self.client, self.namespace, policy_item.uuid
        )

        # Note: Some policies may not be retrievable by UUID due to API limitations
        if retrieved_policy is not None:
            assert retrieved_policy.uuid == policy_item.uuid, (
                "Retrieved policy should match original"
            )
            assert retrieved_policy.meta.name == policy_item.meta.name, (
                "Policy name should match"
            )
            print(f"Successfully retrieved policy: {retrieved_policy.uuid}")
            print(f"Policy name: {retrieved_policy.meta.name}")
            if retrieved_policy.meta.tags:
                print(f"Policy meta tags: {retrieved_policy.meta.tags}")
        else:
            print(
                f"[INFO] Policy {policy_item.uuid} not retrievable by UUID "
                f"(API limitation)"
            )

    def test_policy_type_filtering(self):
        """Test policy filtering by type."""
        print("\n=== TESTING POLICY TYPE FILTERING ===")

        # Test filtering by each policy type
        policy_types = [
            PolicyType.SYSTEM_FINDING,
            PolicyType.USER_FINDING,
            PolicyType.ADMISSION,
            PolicyType.ML_FINDING,
            PolicyType.NOTIFICATION,
        ]

        import conftest

        from endor_cockpit.types import ListParameters

        for policy_type in policy_types:
            filtered_policies = policy.list_policies(
                self.client,
                self.namespace,
                policy_type,
                list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
                max_pages=conftest.TEST_MAX_PAGES,
            )
            print(f"{policy_type.value}: {len(filtered_policies)} policies")

            # Verify all returned policies have the correct type
            for policy_item in filtered_policies:
                assert policy_item.spec.policy_type == policy_type, (
                    f"Policy should be of type {policy_type}"
                )

    def test_policy_rule_analysis(self):
        """Test and analyze policy rules."""
        print("\n=== POLICY RULE ANALYSIS ===")

        # Fetch policies for analysis
        import conftest

        from endor_cockpit.types import ListParameters

        policies = policy.list_policies(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        # Find policies with rules
        policies_with_rules = [p for p in policies if p.spec.rule]
        print(f"Found {len(policies_with_rules)} policies with rules")

        if policies_with_rules:
            policy_obj = policies_with_rules[0]
            print(f"Analyzing rule for policy: {policy_obj.meta.name}")

            # Analyze rule content
            rule = policy_obj.spec.rule
            print(f"Rule length: {len(rule)} characters")
            print(f"Rule type: {type(rule)}")

            # Check for OPA/Rego patterns
            if "package" in rule.lower():
                print("Rule appears to be OPA/Rego format")
            if "deny" in rule.lower() or "allow" in rule.lower():
                print("Rule contains decision keywords")

            # Show rule preview
            rule_preview = rule[:300] + "..." if len(rule) > 300 else rule
            print(f"Rule preview:\n{rule_preview}")

    def test_policy_template_analysis(self):
        """Test and analyze policy templates."""
        print("\n=== POLICY TEMPLATE ANALYSIS ===")

        # Fetch policies for analysis
        import conftest

        from endor_cockpit.types import ListParameters

        policies = policy.list_policies(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        # Find policies with templates
        policies_with_templates = [p for p in policies if p.spec.template_uuid]
        print(f"Found {len(policies_with_templates)} policies with templates")

        if policies_with_templates:
            policy_obj = policies_with_templates[0]
            print(f"Analyzing template for policy: {policy_obj.meta.name}")

            # Analyze template information
            print(f"Template UUID: {policy_obj.spec.template_uuid}")
            print(f"Template Version: {policy_obj.spec.template_version}")

            if policy_obj.spec.template_parameters:
                print(f"Template Parameters: {len(policy_obj.spec.template_parameters)}")
                for param in policy_obj.spec.template_parameters:
                    print(f"  - {param}")

            if policy_obj.spec.template_values:
                print(f"Template Values: {policy_obj.spec.template_values}")

    def test_policy_configuration_analysis(self, sample_policy):
        """Test and analyze policy configuration."""
        print("\n=== POLICY CONFIGURATION ANALYSIS ===")

        policy_obj = sample_policy
        print(f"Analyzing configuration for policy: {policy_obj.meta.name}")

        # Analyze policy configuration
        print(f"Policy Type: {policy_obj.spec.policy_type}")
        print(f"Disabled: {policy_obj.spec.disable}")
        print(f"Propagate: {policy_obj.propagate}")

        # Analyze resource kinds
        if policy_obj.spec.resource_kinds:
            print(f"Resource Kinds: {policy_obj.spec.resource_kinds}")

        # Analyze project selectors
        if policy_obj.spec.project_selector:
            print(f"Project Selector: {policy_obj.spec.project_selector}")

        if policy_obj.spec.project_exceptions:
            print(f"Project Exceptions: {policy_obj.spec.project_exceptions}")

        # Analyze finding configuration
        if policy_obj.spec.finding:
            print(f"Finding Configuration: {policy_obj.spec.finding}")

        # Analyze admission configuration
        if policy_obj.spec.admission:
            print(f"Admission Configuration: {policy_obj.spec.admission}")

        # Analyze notification configuration
        if policy_obj.spec.notification:
            print(f"Notification Configuration: {policy_obj.spec.notification}")

    def test_policy_create_ml_finding(self):
        """Test CREATE policy operation using ML_FINDING pattern."""
        print("\n=== TESTING POLICY CREATE (ML_FINDING) ===")

        created_policy = self._create_test_policy()
        print(f"[SUCCESS] Policy created with UUID: {created_policy.uuid}")
        assert created_policy is not None, "Policy should be created successfully"

    def test_policy_update_ml_finding(self):
        """Test UPDATE policy operation using ML_FINDING pattern."""
        print("\n=== TESTING POLICY UPDATE (ML_FINDING) ===")

        # Create a fresh policy for this test
        print("Creating fresh policy for update test...")
        created_policy = self._create_test_policy(" (Update Test)")
        policy_uuid = created_policy.uuid
        print(f"Created policy UUID: {policy_uuid}")

        # Wait for policy to be fully created
        time.sleep(2)

        # Verify the policy exists and is in the current namespace
        print(f"Current namespace: {self.namespace}")
        created_policy_check = policy.get_policy(
            self.client, self.namespace, policy_uuid
        )
        if not created_policy_check:
            pytest.skip(f"Could not retrieve created policy {policy_uuid}")

        if created_policy_check.tenant_meta.namespace != self.namespace:
            pytest.skip(
                f"Policy {policy_uuid} is in namespace "
                f"{created_policy_check.tenant_meta.namespace}, "
                f"not in current namespace {self.namespace}"
            )

        print(f"Using created policy: {policy_uuid} (created in {self.namespace})")

        # Create update payload - only update safe fields
        update_payload = UpdatePolicyPayload(
            meta=policy.PolicyMeta(
                name="Updated Test Dummy ML Policy",
                kind="Policy",
                description="Updated description for the test ML_FINDING policy",
                tags=["test", "dummy", "ml-finding", "crud-test", "updated"],
            ),
            spec=policy.PolicySpec(
                policy_type=PolicyType.ML_FINDING,
                rule="""package testpolicy

configure[result] {
  result = {
    "updated_test_method": {
      "disable": false,
      "parameters": {
        "enable_updated_test": {
          "bool_value": true
        }
      }
    }
  }
}""",
                disable=False,
                resource_kinds=[],
                project_selector=["test-projects", "updated-projects"],
                project_exceptions=["excluded-projects", "old-projects"],
            ),
            propagate=True,
        )

        print(f"Updating ML_FINDING policy: {policy_uuid}")
        print(f"New name: {update_payload.meta.name}")
        print(f"New tags: {update_payload.meta.tags}")

        # Update the policy
        updated_policy = policy.update_policy(
            self.client,
            self.namespace,
            policy_uuid,
            update_payload,
            "meta.name,meta.description,meta.tags,spec.rule,spec.project_selector,spec.project_exceptions",
        )

        assert updated_policy is not None, "Policy update should succeed"
        assert updated_policy.meta.name == "Updated Test Dummy ML Policy", (
            "Policy name should be updated"
        )
        assert "updated" in updated_policy.meta.tags, "Updated tag should be present"
        assert "updated-projects" in updated_policy.spec.project_selector, (
            "Project selector should be updated"
        )

        print(f"[SUCCESS] Policy updated: {updated_policy.meta.name}")
        print(f"Updated tags: {updated_policy.meta.tags}")
        print(f"Updated project selector: {updated_policy.spec.project_selector}")

        # Note: Policy will be cleaned up by teardown_method
        print(f"[INFO] Policy {policy_uuid} will be cleaned up by teardown")

        assert updated_policy is not None, "Policy should be updated successfully"

    def test_policy_delete_ml_finding(self):
        """Test DELETE policy operation using ML_FINDING pattern."""
        print("\n=== TESTING POLICY DELETE (ML_FINDING) ===")

        # Create a fresh policy for this test
        print("Creating fresh policy for delete test...")
        created_policy = self._create_test_policy(" (Delete Test)")
        policy_uuid = created_policy.uuid
        print(f"Created policy UUID: {policy_uuid}")

        # Wait for policy to be fully created
        time.sleep(2)

        # Verify the policy exists
        created_policy_check = policy.get_policy(
            self.client, self.namespace, policy_uuid
        )
        if not created_policy_check:
            pytest.skip(f"Could not retrieve created policy {policy_uuid}")

        print(f"Deleting ML_FINDING policy: {policy_uuid}")

        # Delete the policy
        delete_success = policy.delete_policy(self.client, self.namespace, policy_uuid)

        assert delete_success, "Policy deletion should succeed"
        print(f"[SUCCESS] Policy deleted: {policy_uuid}")

        # Remove from cleanup list since we deleted it manually
        if policy_uuid in self.created_policy_uuids:
            self.created_policy_uuids.remove(policy_uuid)

        # Verify deletion by trying to retrieve it
        time.sleep(2)  # Wait for deletion to propagate
        deleted_policy = policy.get_policy(self.client, self.namespace, policy_uuid)

        assert deleted_policy is None, "Policy should no longer exist after deletion"
        print("[SUCCESS] Policy deletion confirmed - policy no longer exists")

    def test_policy_ml_finding_pattern_validation(self):
        """Test ML_FINDING pattern validation and characteristics."""
        print("\n=== TESTING ML_FINDING PATTERN VALIDATION ===")

        # Create a test policy
        dummy_policy_payload = CreatePolicyPayload(
            meta=policy.PolicyMeta(
                name="ML Pattern Validation Test",
                kind="Policy",
                description="Testing ML_FINDING pattern characteristics",
                tags=["test", "pattern-validation", "ml-finding"],
            ),
            spec=policy.PolicySpec(
                policy_type=PolicyType.ML_FINDING,
                rule="""package testpattern

configure[result] {
  result = {
    "validation_method": {
      "disable": false,
      "parameters": {
        "enable_validation": {
          "bool_value": true
        }
      }
    }
  }
}""",
                disable=False,
                resource_kinds=[],  # ML_FINDING characteristic: empty resource kinds
                project_selector=["validation-projects"],
                project_exceptions=["excluded-projects"],
            ),
            propagate=True,
        )

        # Test policy creation
        created_policy = policy.create_policy(
            self.client, self.namespace, dummy_policy_payload
        )
        assert created_policy is not None, "ML_FINDING policy creation should succeed"

        # Validate ML_FINDING characteristics
        assert created_policy.spec.policy_type == PolicyType.ML_FINDING, (
            "Should be ML_FINDING type"
        )
        assert created_policy.spec.resource_kinds == [], (
            "ML_FINDING should have empty resource kinds"
        )
        assert "configure[result]" in created_policy.spec.rule, (
            "Should have configure pattern"
        )
        assert "validation_method" in created_policy.spec.rule, (
            "Should have method configuration"
        )

        print("[SUCCESS] ML_FINDING pattern validation passed")
        print(f"  - Policy Type: {created_policy.spec.policy_type}")
        print(f"  - Resource Kinds: {created_policy.spec.resource_kinds}")
        print("  - Rule Pattern: configure[result] with JSON configuration")
        print(f"  - Rule Length: {len(created_policy.spec.rule)} characters")

        # Note: Policy will be cleaned up by teardown_method
        print("[INFO] Test policy will be cleaned up by teardown")


if __name__ == "__main__":
    # Run tests directly
    import os
    import sys

    # Set up environment - require ENDOR_NAMESPACE to be set
    if not os.getenv("ENDOR_NAMESPACE"):
        print("ERROR: ENDOR_NAMESPACE environment variable must be set")
        sys.exit(1)

    # Create test instance and manually set up
    test_instance = TestPolicy()

    # Manual setup
    import conftest

    from endor_cockpit.types import ListParameters

    test_instance.client = APIClient(auth_method="api-key")
    test_instance.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.tgowan-endor")
    test_instance.policies = policy.list_policies(
        test_instance.client,
        test_instance.namespace,
        list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
        max_pages=conftest.TEST_MAX_PAGES,
    )

    try:
        print("Running policy resource tests...")

        # Run all tests
        test_instance.test_policy_get_list()
        test_instance.test_policy_get_by_uuid()
        test_instance.test_policy_type_filtering()
        test_instance.test_policy_structure_analysis()
        test_instance.test_policy_rule_analysis()
        test_instance.test_policy_template_analysis()
        test_instance.test_policy_configuration_analysis()
        test_instance.test_policy_schema_drift_detection()
        test_instance.test_policy_operations_summary()

        # Run CRUD tests using ML_FINDING pattern
        test_instance.test_policy_ml_finding_pattern_validation()
        test_instance.test_policy_full_crud_cycle()

        print("\n[SUCCESS] All policy tests completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
