"""
Test cleanup mechanisms for integration tests.

This module tests that the cleanup mechanisms in the test suite
properly clean up resources created during tests.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import policy
from endor_cockpit.resources.policy import (
    CreatePolicyPayload,
    PolicyType,
)


@pytest.mark.integration
class TestCleanupMechanisms:
    """Test cleanup mechanisms for integration tests."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = APIClient()
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")
        self.created_policy_uuids = []

    def teardown_method(self):
        """Clean up any resources created during tests."""
        # Clean up policies
        for policy_uuid in self.created_policy_uuids:
            try:
                policy.delete_policy(self.client, self.namespace, policy_uuid)
                print(f"[CLEANUP] Deleted test policy: {policy_uuid}")
            except Exception as e:
                print(f"[WARNING] Failed to delete test policy {policy_uuid}: {e}")

        self.created_policy_uuids.clear()

    def test_policy_cleanup_tracking(self):
        """Test that policy cleanup tracking works correctly."""
        print("\n=== TESTING POLICY CLEANUP TRACKING ===")

        # Create a test policy
        policy_payload = CreatePolicyPayload(
            meta=policy.PolicyMeta(
                name="Cleanup Test Policy",
                kind="Policy",
                description="Test policy for cleanup mechanism testing",
                tags=["test", "cleanup-test", "crud-test"],
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
                resource_kinds=[],
                project_selector=["test-projects"],
                project_exceptions=["excluded-projects"],
            ),
            propagate=True,
        )

        # Create the policy
        created_policy = policy.create_policy(
            self.client, self.namespace, policy_payload
        )

        assert created_policy is not None, "Policy creation should succeed"
        policy_uuid = created_policy.uuid

        # Track for cleanup
        self.created_policy_uuids.append(policy_uuid)

        print(f"[SUCCESS] Created and tracked policy: {policy_uuid}")

        # Verify the policy exists
        retrieved_policy = policy.get_policy(self.client, self.namespace, policy_uuid)
        assert retrieved_policy is not None, "Policy should exist after creation"

        print("[SUCCESS] Policy cleanup tracking test passed")

    def test_cleanup_mechanism_integration(self):
        """Test that cleanup mechanisms work together correctly."""
        print("\n=== TESTING CLEANUP MECHANISM INTEGRATION ===")

        # Create multiple test policies
        test_policies = []

        # Create 2 test policies
        for i in range(2):
            policy_payload = CreatePolicyPayload(
                meta=policy.PolicyMeta(
                    name=f"Integration Cleanup Test Policy {i + 1}",
                    kind="Policy",
                    description=f"Test policy {i + 1} for integration cleanup testing",
                    tags=["test", "integration-cleanup", "crud-test"],
                ),
                spec=policy.PolicySpec(
                    policy_type=PolicyType.ML_FINDING,
                    rule=f"""package testpolicy{i + 1}

configure[result] {{
  result = {{
    "test_method_{i + 1}": {{
      "disable": false,
      "parameters": {{
        "enable_test_{i + 1}": {{
          "bool_value": true
        }}
      }}
    }}
  }}
}}""",
                    disable=False,
                    resource_kinds=[],
                    project_selector=[f"test-projects-{i + 1}"],
                    project_exceptions=[f"excluded-projects-{i + 1}"],
                ),
                propagate=True,
            )

            created_policy = policy.create_policy(
                self.client, self.namespace, policy_payload
            )
            if created_policy:
                test_policies.append(created_policy)
                self.created_policy_uuids.append(created_policy.uuid)

        print(f"[SUCCESS] Created {len(test_policies)} policies")

        # Verify all policies exist
        for policy_obj in test_policies:
            retrieved = policy.get_policy(self.client, self.namespace, policy_obj.uuid)
            assert retrieved is not None, f"Policy {policy_obj.uuid} should exist"

        print("[SUCCESS] All policies verified to exist")

        # Note: Policies will be cleaned up by teardown_method
        print("[INFO] Policies will be cleaned up by teardown_method")

        print("[SUCCESS] Cleanup mechanism integration test passed")

    def test_cleanup_error_handling(self):
        """Test that cleanup mechanisms handle errors gracefully."""
        print("\n=== TESTING CLEANUP ERROR HANDLING ===")

        # Create a policy
        policy_payload = CreatePolicyPayload(
            meta=policy.PolicyMeta(
                name="Error Handling Test Policy",
                kind="Policy",
                description="Test policy for cleanup error handling",
                tags=["test", "error-handling", "crud-test"],
            ),
            spec=policy.PolicySpec(
                policy_type=PolicyType.ML_FINDING,
                rule="""package testpolicy

configure[result] {
  result = {
    "error_test_method": {
      "disable": false,
      "parameters": {
        "enable_error_test": {
          "bool_value": true
        }
      }
    }
  }
}""",
                disable=False,
                resource_kinds=[],
                project_selector=["error-test-projects"],
                project_exceptions=["error-excluded-projects"],
            ),
            propagate=True,
        )

        created_policy = policy.create_policy(
            self.client, self.namespace, policy_payload
        )

        assert created_policy is not None, "Policy creation should succeed"
        policy_uuid = created_policy.uuid

        # Track for cleanup
        self.created_policy_uuids.append(policy_uuid)

        # Manually delete the policy to simulate it being deleted elsewhere
        policy.delete_policy(self.client, self.namespace, policy_uuid)

        # Remove from tracking since we deleted it manually
        self.created_policy_uuids.remove(policy_uuid)

        # Now try to clean up the already-deleted policy (should handle gracefully)
        try:
            policy.delete_policy(self.client, self.namespace, policy_uuid)
            print("[WARNING] Policy deletion succeeded when it should have failed")
        except Exception as e:
            print(f"[EXPECTED] Policy deletion failed as expected: {e}")

        print("[SUCCESS] Cleanup error handling test passed")


if __name__ == "__main__":
    # Run tests directly
    import os

    # Set up environment
    os.environ.setdefault("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")

    # Create test instance and manually set up
    test_instance = TestCleanupMechanisms()

    # Manual setup
    test_instance.client = APIClient()
    test_instance.namespace = os.getenv(
        "ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit"
    )
    test_instance.created_policy_uuids = []

    try:
        print("Running cleanup mechanism tests...")

        # Run all tests
        test_instance.test_policy_cleanup_tracking()
        test_instance.test_cleanup_mechanism_integration()
        test_instance.test_cleanup_error_handling()

        print("\n[SUCCESS] All cleanup mechanism tests completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        # Ensure cleanup happens even if tests fail
        test_instance.teardown_method()
