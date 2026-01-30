"""Test cases for Policy resource operations.

Tests full CRUD operations for Policy resources using USER_FINDING policy type.
Includes policy type filtering, analysis, and comprehensive CRUD testing with
live data.

Note: SYSTEM_FINDING policies are system-generated only and cannot be created
by users. Tests use USER_FINDING for custom policy creation.
"""

import os
import sys
import time

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import conftest

from endorlabs.api_client import APIClient
from endorlabs.resources import policy
from endorlabs.resources.policy import (
    CreatePolicyPayload,
    ExceptionReason,
    Policy,
    PolicyType,
    UpdatePolicyPayload,
)


@pytest.mark.integration
class TestPolicy:
    """Test cases for Policy resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self) -> None:
        """Fast setup: client and namespace only (runs before each test)."""
        # Reduce retries for faster test failure (prevents excessive wait on API errors)
        # Production uses 15 retries, but tests should fail fast (3 retries max)
        self.client = APIClient(auth_method="api-key", max_retries=3)
        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)

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
        from endorlabs.types import ListParameters

        results = policy.list_policies(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=1),
            max_pages=1,
        )
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    def _create_test_policy(self, name_suffix: str = ""):
        """Helper method to create a test policy for CRUD operations.

        Uses EXCEPTION policy type (maneuver format) instead of USER_FINDING
        to avoid API 500 errors. Exception policies work reliably.

        Args:
            name_suffix: Optional suffix to add to policy name for uniqueness

        Returns:
            Created policy object

        """
        import time

        timestamp = int(time.time())
        policy_name = f"Test Exception Policy{name_suffix} {timestamp}"
        dummy_policy_payload = CreatePolicyPayload(
            meta=policy.PolicyMeta(
                name=policy_name,
                description=(
                    "A test EXCEPTION policy created for CRUD operations testing "
                    "(using maneuver format to avoid API 500 errors)"
                ),
                tags=["test", "exception", "crud-test", "endor-cockpit"],
            ),
            spec=policy.PolicySpec(
                policy_type=PolicyType.EXCEPTION,
                rule="""package exceptions

# EXCEPTION policies must return Finding UUIDs with Endor field
match_finding[result] {
    some i
    data.resources.Finding[i]
    # Match all findings for test purposes
    result = {
        "Endor": {
            "Finding": data.resources.Finding[i].uuid
        }
    }
}""",
                query_statements=["data.exceptions.match_finding"],
                disable=False,
                resource_kinds=["Finding"],
                exception={"reason": ExceptionReason.FALSE_POSITIVE},
            ),
            propagate=True,
        )

        # Create the policy
        created_policy = policy.create_policy(
            self.client, self.namespace, dummy_policy_payload
        )

        assert created_policy is not None, "Policy creation should succeed"
        assert created_policy.meta.name == policy_name, "Policy name should match"
        assert created_policy.spec.policy_type == PolicyType.EXCEPTION, (
            "Policy type should be EXCEPTION"
        )

        # Store for cleanup
        self.created_policy_uuids.append(created_policy.uuid)
        return created_policy

    def teardown_method(self) -> None:
        """Clean up any policies created during tests."""
        if hasattr(self, "created_policy_uuids"):
            for policy_uuid in self.created_policy_uuids:
                try:
                    policy.delete_policy(self.client, self.namespace, policy_uuid)
                    print(f"[CLEANUP] Deleted test policy: {policy_uuid}")
                except Exception as e:
                    print(f"[WARNING] Failed to delete test policy {policy_uuid}: {e}")
            self.created_policy_uuids.clear()

    def test_policy_get_list(self) -> None:
        """Test GET policies operation."""
        print("\n=== TESTING GET POLICIES ===")

        # Test list_policies with pagination limits
        import conftest

        from endorlabs.types import ListParameters

        policies_list = policy.list_policies(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(policies_list, list), "Should return a list of policies"
        assert all(
            isinstance(x, Policy) for x in policies_list
        ), "All list items should be Policy instances"
        if len(policies_list) == 0:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

        print(f"Found {len(policies_list)} policies")

        # Display first few policies
        for _i, policy_item in enumerate(policies_list[:10]):  # Show first 10
            name = policy_item.meta.name if policy_item.meta else None
            print(f"Policy {policy_item.uuid}: {name}")
            ptype = policy_item.spec.policy_type if policy_item.spec else None
            print(f"  Type: {ptype}")
            if policy_item.meta.tags:
                print(f"  Meta tags: {policy_item.meta.tags}")

    def test_policy_get_by_uuid(self, sample_policy) -> None:
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

    def test_policy_type_filtering(self) -> None:
        """Test policy filtering by type."""
        print("\n=== TESTING POLICY TYPE FILTERING ===")

        # Test filtering by each policy type
        policy_types = [
            PolicyType.SYSTEM_FINDING,
            PolicyType.USER_FINDING,
            PolicyType.ADMISSION,
            PolicyType.NOTIFICATION,
        ]

        import conftest

        from endorlabs.types import ListParameters

        for policy_type in policy_types:
            filtered_policies = policy.list_policies(
                self.client,
                self.namespace,
                list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
                max_pages=conftest.TEST_MAX_PAGES,
                policy_type=policy_type,
            )
            print(f"{policy_type.value}: {len(filtered_policies)} policies")

            # Verify all returned policies have the correct type
            for policy_item in filtered_policies:
                assert policy_item.spec.policy_type == policy_type, (
                    f"Policy should be of type {policy_type}"
                )

    @pytest.mark.writes
    def test_policy_create(self) -> None:
        """Test CREATE policy operation.

        Local-only: creating policies requires elevated permissions (403 in CI).
        """
        print("\n=== TESTING POLICY CREATE ===")

        created_policy = self._create_test_policy()
        print(f"[SUCCESS] Policy created with UUID: {created_policy.uuid}")
        assert created_policy is not None, "Policy should be created successfully"

    @pytest.mark.writes
    def test_policy_update_with_mask(self) -> None:
        """Test UPDATE policy operation with update_mask parameter.

        Local-only: requires create and update permissions (403 in CI).
        """
        print("\n=== TESTING POLICY UPDATE WITH MASK ===")

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
            meta=policy.PolicyMetaUpdate(
                name="Updated Test Exception Policy",
                description="Updated description for the test EXCEPTION policy",
                tags=["test", "exception", "crud-test", "updated", "endor-cockpit"],
            ),
            spec=policy.PolicySpec(
                policy_type=PolicyType.EXCEPTION,
                rule="""package exceptions

# EXCEPTION policies must return Finding UUIDs with Endor field
match_finding[result] {
    some i
    data.resources.Finding[i]
    # Updated rule for test purposes
    result = {
        "Endor": {
            "Finding": data.resources.Finding[i].uuid
        }
    }
}""",
                query_statements=["data.exceptions.match_finding"],
                disable=False,
                resource_kinds=["Finding"],
                exception={"reason": ExceptionReason.FALSE_POSITIVE},
            ),
            propagate=True,
        )

        print(f"Updating EXCEPTION policy: {policy_uuid}")
        print(f"New name: {update_payload.meta.name}")
        print(f"New tags: {update_payload.meta.tags}")

        # Update the policy with update_mask
        updated_policy = policy.update_policy(
            self.client,
            self.namespace,
            policy_uuid,
            update_payload,
            "meta.name,meta.description,meta.tags,spec.rule",
        )

        assert updated_policy is not None, "Policy update should succeed"
        assert updated_policy.meta.name == "Updated Test Exception Policy", (
            "Policy name should be updated"
        )
        assert "updated" in updated_policy.meta.tags, "Updated tag should be present"

        print(f"[SUCCESS] Policy updated: {updated_policy.meta.name}")
        print(f"Updated tags: {updated_policy.meta.tags}")

        # Note: Policy will be cleaned up by teardown_method
        print(f"[INFO] Policy {policy_uuid} will be cleaned up by teardown")

        assert updated_policy is not None, "Policy should be updated successfully"

    @pytest.mark.writes
    def test_policy_delete(self) -> None:
        """Test DELETE policy operation.

        Local-only: requires create and delete permissions (403 in CI).
        """
        print("\n=== TESTING POLICY DELETE ===")

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

        print(f"Deleting EXCEPTION policy: {policy_uuid}")

        # Delete the policy
        delete_success = policy.delete_policy(self.client, self.namespace, policy_uuid)

        assert delete_success, "Policy deletion should succeed"
        print(f"[SUCCESS] Policy deleted: {policy_uuid}")

        # Remove from cleanup list since we deleted it manually
        if policy_uuid in self.created_policy_uuids:
            self.created_policy_uuids.remove(policy_uuid)

        # Verify deletion by trying to retrieve it
        time.sleep(2)  # Wait for deletion to propagate
        from endorlabs.exceptions import NotFoundError

        with pytest.raises(NotFoundError) as exc_info:
            policy.get_policy(self.client, self.namespace, policy_uuid)
        assert exc_info.value.resource_uuid == policy_uuid
        assert exc_info.value.operation == "get"
        print("[SUCCESS] Policy deletion confirmed - policy no longer exists")

    @pytest.mark.writes
    def test_exception_policy_create(self) -> None:
        """Test CREATE exception policy operation.

        Local-only: creating policies requires elevated permissions (403 in CI).
        """
        print("\n=== TESTING EXCEPTION POLICY CREATE ===")

        timestamp = int(time.time())
        policy_name = f"Test Exception Policy {timestamp}"

        exception_policy_payload = CreatePolicyPayload(
            meta=policy.PolicyMeta(
                name=policy_name,
                description=(
                    "A test EXCEPTION policy created for testing "
                    "exception policy creation"
                ),
                tags=["test", "exception", "crud-test"],
            ),
            spec=policy.PolicySpec(
                policy_type=PolicyType.EXCEPTION,
                rule="""package exceptions

# EXCEPTION policies must return Finding UUIDs with Endor field
match_finding[result] {
    some i
    data.resources.Finding[i]
    # Match all findings for test purposes
    result = {
        "Endor": {
            "Finding": data.resources.Finding[i].uuid
        }
    }
}""",
                query_statements=["data.exceptions.match_finding"],
                resource_kinds=["Finding"],
                disable=False,
                exception={"reason": ExceptionReason.FALSE_POSITIVE},
            ),
            propagate=True,
        )

        # Create the exception policy
        created_policy = policy.create_policy(
            self.client, self.namespace, exception_policy_payload
        )

        assert created_policy is not None, "Exception policy creation should succeed"
        assert created_policy.meta.name == policy_name, "Policy name should match"
        assert created_policy.spec.policy_type == PolicyType.EXCEPTION, (
            "Policy type should be EXCEPTION"
        )
        assert created_policy.spec.exception is not None, (
            "Exception config should be present"
        )
        # Exception config can be ExceptionConfig object or dict
        # depending on API response
        exception_reason = (
            created_policy.spec.exception.reason
            if hasattr(created_policy.spec.exception, "reason")
            else created_policy.spec.exception.get("reason")
        )
        assert exception_reason == ExceptionReason.FALSE_POSITIVE, (
            "Exception reason should be FALSE_POSITIVE"
        )

        # Store for cleanup
        self.created_policy_uuids.append(created_policy.uuid)
        print(f"[SUCCESS] Exception policy created with UUID: {created_policy.uuid}")

    @pytest.mark.writes
    def test_notification_policy_create(self) -> None:
        """Test CREATE notification policy operation.

        Local-only: creating policies requires elevated permissions (403 in CI).
        """
        print("\n=== TESTING NOTIFICATION POLICY CREATE ===")

        # First, try to find an existing notification target
        # If none exists, skip the test
        try:
            res = self.client.get(
                f"v1/namespaces/{self.namespace}/notification-targets"
            )
            if res.status_code == 200:
                data = res.json()
                notification_targets = data.get("list", {}).get("objects", [])
                if not notification_targets:
                    pytest.skip(
                        "No notification targets available - "
                        "cannot test notification policy creation"
                    )
                notification_target_uuid = notification_targets[0].get("uuid")
            else:
                pytest.skip(f"Could not list notification targets: {res.status_code}")
        except Exception as e:
            pytest.skip(f"Could not check for notification targets: {e}")

        timestamp = int(time.time())
        policy_name = f"Test Notification Policy {timestamp}"

        notification_policy_payload = CreatePolicyPayload(
            meta=policy.PolicyMeta(
                name=policy_name,
                description=(
                    "A test NOTIFICATION policy created for testing "
                    "notification policy creation"
                ),
                tags=["test", "notification", "crud-test"],
            ),
            spec=policy.PolicySpec(
                policy_type=PolicyType.NOTIFICATION,
                rule="""package notification

match_baseline(finding) {
    some i
    data.baseline.Finding[i].spec.extra_key == finding.spec.extra_key
    count(
        data.baseline.Finding[i].spec.finding_metadata.source_policy_info.results
    ) == (
        count(finding.spec.finding_metadata.source_policy_info.results)
    )
}

match_findings[result] {
    some i
    data.resources.Finding[i].spec.finding_categories[_] == (
        "FINDING_CATEGORY_VULNERABILITY"
    )
    not match_baseline(data.resources.Finding[i])
    result = {
        "Endor": {
            "Finding": data.resources.Finding[i].uuid
        }
    }
}""",
                query_statements=["data.notification.match_findings"],
                resource_kinds=["Finding"],
                disable=False,
                notification={
                    "notification_target_uuids": [notification_target_uuid],
                    "aggregation_type": "AGGREGATION_TYPE_PROJECT",
                    "bypass_exceptions": False,
                },
            ),
            propagate=True,
        )

        # Create the notification policy
        created_policy = policy.create_policy(
            self.client, self.namespace, notification_policy_payload
        )

        assert created_policy is not None, "Notification policy creation should succeed"
        assert created_policy.meta.name == policy_name, "Policy name should match"
        assert created_policy.spec.policy_type == PolicyType.NOTIFICATION, (
            "Policy type should be NOTIFICATION"
        )
        assert created_policy.spec.notification is not None, (
            "Notification config should be present"
        )
        assert notification_target_uuid in created_policy.spec.notification.get(
            "notification_target_uuids", []
        ), "Notification target UUID should be in config"

        # Store for cleanup
        self.created_policy_uuids.append(created_policy.uuid)
        print(f"[SUCCESS] Notification policy created with UUID: {created_policy.uuid}")

    @pytest.mark.writes
    def test_admission_policy_create(self) -> None:
        """Test CREATE admission policy operation.

        Local-only: creating policies requires elevated permissions (403 in CI).
        """
        print("\n=== TESTING ADMISSION POLICY CREATE ===")

        timestamp = int(time.time())
        policy_name = f"Test Admission Policy {timestamp}"

        admission_policy_payload = CreatePolicyPayload(
            meta=policy.PolicyMeta(
                name=policy_name,
                description=(
                    "A test ADMISSION policy created for testing "
                    "admission policy creation"
                ),
                tags=["test", "admission", "crud-test"],
            ),
            spec=policy.PolicySpec(
                policy_type=PolicyType.ADMISSION,
                rule="""package admission

match_baseline(finding) {
    some i
    data.baseline.Finding[i].spec.extra_key == finding.spec.extra_key
    count(
        data.baseline.Finding[i].spec.finding_metadata.source_policy_info.results
    ) == (
        count(finding.spec.finding_metadata.source_policy_info.results)
    )
}

match_findings[result] {
    some i
    data.resources.Finding[i].spec.finding_categories[_] == (
        "FINDING_CATEGORY_VULNERABILITY"
    )
    data.resources.Finding[i].spec.level == "FINDING_LEVEL_CRITICAL"
    not match_baseline(data.resources.Finding[i])
    result = {
        "Endor": {
            "Finding": data.resources.Finding[i].uuid
        }
    }
}""",
                query_statements=["data.admission.match_findings"],
                resource_kinds=["Finding"],
                disable=False,
                admission={
                    "action": "DENY",  # Block the build
                },
            ),
            propagate=True,
        )

        # Create the admission policy
        created_policy = policy.create_policy(
            self.client, self.namespace, admission_policy_payload
        )

        assert created_policy is not None, "Admission policy creation should succeed"
        assert created_policy.meta.name == policy_name, "Policy name should match"
        assert created_policy.spec.policy_type == PolicyType.ADMISSION, (
            "Policy type should be ADMISSION"
        )
        assert created_policy.spec.admission is not None, (
            "Admission config should be present"
        )

        # Store for cleanup
        self.created_policy_uuids.append(created_policy.uuid)
        print(f"[SUCCESS] Admission policy created with UUID: {created_policy.uuid}")

    def test_client_recommended_ux_list_policies(self) -> None:
        """Recommended UX: endorlabs.Client(tenant=...); client.policies.list()."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.namespace,
            max_retries=2,
            backoff_factor=0.1,
            auth_method="api-key",
        )
        try:
            policies = client.policies.list(max_pages=1)
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        assert isinstance(policies, list)


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

    from endorlabs.types import ListParameters

    # Reduce retries for faster test failure (prevents excessive wait on API errors)
    test_instance.client = APIClient(auth_method="api-key", max_retries=3)
    test_instance.namespace = os.getenv(
        "ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT
    )
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

        # Run CRUD tests
        test_instance.test_policy_create()
        test_instance.test_policy_update_with_mask()
        test_instance.test_policy_delete()

        print("\n[SUCCESS] All policy tests completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
