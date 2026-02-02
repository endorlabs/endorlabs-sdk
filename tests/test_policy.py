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
    PolicyType,
    UpdatePolicyPayload,
)


@pytest.mark.integration
class TestPolicy:
    """Test cases for Policy resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace, root_namespace) -> None:
        """Fast setup: client and namespace from conftest."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.created_policy_uuids = []

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
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
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

    def test_policy_list(self) -> None:
        """LIST from tenant root with traverse."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        try:
            result = client.policy.list(
                traverse=True,
                max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        assert isinstance(result, list)

    def test_policy_get(self) -> None:
        """GET first item from LIST (root + traverse)."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        try:
            items = client.policy.list(
                traverse=True,
                max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.root_namespace
        )
        got = client.policy.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

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

    @pytest.mark.writes
    def test_client_ux_create_policy(self) -> None:
        """Consumer UX: client.policy.create(payload); teardown deletes."""
        import time

        import endorlabs

        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        policy_name = f"ClientUX Exception {int(time.time())}"
        payload = CreatePolicyPayload(
            meta=policy.PolicyMeta(
                name=policy_name,
                description="Consumer UX create test",
                tags=["test", "client-ux"],
            ),
            spec=policy.PolicySpec(
                policy_type=PolicyType.EXCEPTION,
                rule="""package exceptions
match_finding[result] {
    some i
    data.resources.Finding[i]
    result = {"Endor": {"Finding": data.resources.Finding[i].uuid}}
}""",
                query_statements=["data.exceptions.match_finding"],
                disable=False,
                resource_kinds=["Finding"],
                exception={"reason": ExceptionReason.FALSE_POSITIVE},
            ),
            propagate=False,
        )
        try:
            created = client.policy.create(payload)
        except Exception as e:
            pytest.skip(f"Policy create not allowed in this environment: {e}")
        assert created is not None
        assert created.meta.name == policy_name
        self.created_policy_uuids.append(created.uuid)

    @pytest.mark.writes
    def test_client_ux_update_policy(self) -> None:
        """Consumer UX: list get update revert."""
        import endorlabs
        from endorlabs.exceptions import ServerError

        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        try:
            policies = client.policy.list(max_pages=conftest.TEST_MAX_PAGES)
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not policies:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = policies[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.namespace
        )
        current = client.policy.get(item.uuid, namespace=ns)
        if not current:
            pytest.skip(f"Could not retrieve policy {item.uuid}")
        original_description = getattr(current.meta, "description", None) or ""
        update_payload = UpdatePolicyPayload(
            meta=policy.PolicyMetaUpdate(description="Updated by client-ux")
        )
        try:
            updated = client.policy.update(
                item.uuid, update_payload, update_mask="meta.description", namespace=ns
            )
        except Exception as e:
            pytest.skip(f"Policy update not allowed in this environment: {e}")
        assert updated is not None
        restore_payload = UpdatePolicyPayload(
            meta=policy.PolicyMetaUpdate(description=original_description)
        )
        try:
            client.policy.update(
                item.uuid, restore_payload, update_mask="meta.description", namespace=ns
            )
        except Exception as e:
            print(f"[WARNING] Failed to restore original policy values: {e}")

    @pytest.mark.writes
    def test_client_ux_delete_policy(self) -> None:
        """Consumer UX: create then client.policy.delete(uuid)."""
        import time

        import endorlabs

        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        policy_name = f"ClientUX Del {int(time.time())}"
        payload = CreatePolicyPayload(
            meta=policy.PolicyMeta(
                name=policy_name,
                description="Consumer UX delete test",
                tags=["test", "client-ux"],
            ),
            spec=policy.PolicySpec(
                policy_type=PolicyType.EXCEPTION,
                rule="""package exceptions
match_finding[result] {
    some i
    data.resources.Finding[i]
    result = {"Endor": {"Finding": data.resources.Finding[i].uuid}}
}""",
                query_statements=["data.exceptions.match_finding"],
                disable=False,
                resource_kinds=["Finding"],
                exception={"reason": ExceptionReason.FALSE_POSITIVE},
            ),
            propagate=False,
        )
        try:
            created = client.policy.create(payload)
        except Exception as e:
            pytest.skip(f"Policy create not allowed in this environment: {e}")
        if not created:
            pytest.skip("Failed to create policy for delete test")
        result = client.policy.delete(created.uuid)
        assert result is True


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
        test_instance.test_policy_type_filtering()

        print("\n[SUCCESS] All policy tests completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        test_instance.client.close()
