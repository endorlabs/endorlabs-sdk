"""Test cases for AuthorizationPolicy resource operations.

Tests full CRUD operations for AuthorizationPolicy resources using various
system roles and permission configurations.
Includes validation, filtering, and comprehensive CRUD testing with live data.
"""

import os
import sys
import time

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import conftest

from endorlabs.api_client import APIClient
from endorlabs.resources import authorization_policy
from endorlabs.resources.authorization_policy import (
    AuthorizationPolicyMeta,
    AuthorizationPolicyPermissions,
    AuthorizationPolicySpec,
    CreateAuthorizationPolicyPayload,
    SystemRole,
    UpdateAuthorizationPolicyPayload,
)


@pytest.mark.integration
class TestAuthorizationPolicy:
    """Test cases for AuthorizationPolicy resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self) -> None:
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)
        self.created_policy_uuids = []  # Track created policies for cleanup

        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

    def teardown_method(self) -> None:
        """Clean up any policies created during tests."""
        if hasattr(self, "created_policy_uuids"):
            for policy_uuid in self.created_policy_uuids:
                try:
                    authorization_policy.delete_authorization_policy(
                        self.client, self.namespace, policy_uuid
                    )
                    print(f"[CLEANUP] Deleted test authorization policy: {policy_uuid}")
                except Exception as e:
                    print(
                        f"[WARNING] Failed to delete test authorization "
                        f"policy {policy_uuid}: {e}"
                    )
            self.created_policy_uuids.clear()

    def test_authorization_policy_get_list(self) -> None:
        """Test GET authorization policies operation."""
        print("\n=== TESTING AUTHORIZATION POLICY LIST ===")

        import conftest

        from endorlabs.types import ListParameters

        policies = authorization_policy.list_authorization_policies(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )

        assert isinstance(policies, list), "Should return a list"
        print(f"Found {len(policies)} authorization policies")

        if policies:
            policy = policies[0]
            assert hasattr(policy, "uuid"), "Policy should have uuid"
            assert hasattr(policy, "meta"), "Policy should have meta"
            assert hasattr(policy, "spec"), "Policy should have spec"
            assert hasattr(policy, "tenant_meta"), "Policy should have tenant_meta"
            print(f"Sample policy UUID: {policy.uuid}")
            print(f"Sample policy name: {policy.meta.name}")

    def test_authorization_policy_get_by_uuid(self) -> None:
        """Test GET authorization policy by UUID operation."""
        print("\n=== TESTING AUTHORIZATION POLICY GET BY UUID ===")

        import conftest

        from endorlabs.types import ListParameters

        policies = authorization_policy.list_authorization_policies(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        if not policies:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

        test_policy = policies[0]
        retrieved = authorization_policy.get_authorization_policy(
            self.client, self.namespace, test_policy.uuid
        )

        assert retrieved is not None, "Should retrieve policy"
        assert retrieved.uuid == test_policy.uuid, "UUID should match"
        assert retrieved.meta.name == test_policy.meta.name, "Name should match"
        print(f"Retrieved policy: {retrieved.meta.name}")

    @pytest.mark.writes
    def test_authorization_policy_create_with_role(self) -> None:
        """Test CREATE authorization policy operation with system role.

        Local-only: creating auth policies requires elevated permissions (403 in CI).
        """
        print("\n=== TESTING AUTHORIZATION POLICY CREATE (WITH ROLE) ===")

        # Create test policy with CODE_SCANNER role
        timestamp = int(time.time())
        test_policy_payload = CreateAuthorizationPolicyPayload(
            meta=AuthorizationPolicyMeta(
                name=f"test-auth-policy-{timestamp}",
                description="Test authorization policy created for CRUD testing",
                tags=["test", "crud-test"],
            ),
            spec=AuthorizationPolicySpec(
                clause=["test@endor.ai"],
                target_namespaces=[self.namespace],
                propagate=False,
                permissions=AuthorizationPolicyPermissions(
                    roles=[SystemRole.CODE_SCANNER.value]
                ),
            ),
            propagate=False,
        )

        print(f"Creating authorization policy: {test_policy_payload.meta.name}")
        print(f"Role: {SystemRole.CODE_SCANNER.value}")

        # Create the policy
        created_policy = authorization_policy.create_authorization_policy(
            self.client, self.namespace, test_policy_payload
        )

        assert created_policy is not None, "Policy creation should succeed"
        assert created_policy.meta.name == test_policy_payload.meta.name, (
            "Policy name should match"
        )
        assert (
            created_policy.spec.permissions.roles
            == test_policy_payload.spec.permissions.roles
        ), "Roles should match"

        # Track for cleanup
        self.created_policy_uuids.append(created_policy.uuid)
        print(f"Created policy UUID: {created_policy.uuid}")

    @pytest.mark.writes
    def test_authorization_policy_create_with_resource_permissions(self) -> None:
        """Test CREATE authorization policy with resource-specific permissions.

        Local-only: creating auth policies requires elevated permissions (403 in CI).
        """
        print(
            "\n=== TESTING AUTHORIZATION POLICY CREATE (WITH RESOURCE PERMISSIONS) ==="
        )

        timestamp = int(time.time())
        test_policy_payload = CreateAuthorizationPolicyPayload(
            meta=AuthorizationPolicyMeta(
                name=f"test-auth-policy-resource-{timestamp}",
                description="Test authorization policy with resource permissions",
            ),
            spec=AuthorizationPolicySpec(
                clause=["test@endor.ai"],
                target_namespaces=[self.namespace],
                propagate=False,
                permissions=AuthorizationPolicyPermissions(
                    rules={
                        "repository": {"methods": ["METHOD_READ", "METHOD_CREATE"]},
                        "finding": {"methods": ["METHOD_READ"]},
                    }
                ),
            ),
            propagate=False,
        )

        print(f"Creating authorization policy: {test_policy_payload.meta.name}")
        print("Resource permissions: repository (READ, CREATE), finding (READ)")

        # Create the policy
        created_policy = authorization_policy.create_authorization_policy(
            self.client, self.namespace, test_policy_payload
        )

        assert created_policy is not None, "Policy creation should succeed"
        assert created_policy.spec.permissions.rules is not None, "Rules should be set"

        # Track for cleanup
        self.created_policy_uuids.append(created_policy.uuid)
        print(f"Created policy UUID: {created_policy.uuid}")

    @pytest.mark.writes
    def test_authorization_policy_update(self) -> None:
        """Test UPDATE authorization policy operation.

        Local-only: requires create (and update) permissions (403 in CI).
        """
        print("\n=== TESTING AUTHORIZATION POLICY UPDATE ===")

        # First create a policy to update
        timestamp = int(time.time())
        create_payload = CreateAuthorizationPolicyPayload(
            meta=AuthorizationPolicyMeta(
                name=f"test-auth-policy-update-{timestamp}",
                description="Test policy for update testing",
            ),
            spec=AuthorizationPolicySpec(
                clause=["test@endor.ai"],
                target_namespaces=[self.namespace],
                propagate=False,
                permissions=AuthorizationPolicyPermissions(
                    roles=[SystemRole.READ_ONLY.value]
                ),
            ),
            propagate=False,
        )

        created = authorization_policy.create_authorization_policy(
            self.client, self.namespace, create_payload
        )
        if not created:
            pytest.skip("Failed to create policy for update test")

        self.created_policy_uuids.append(created.uuid)

        # Update the policy
        update_payload = UpdateAuthorizationPolicyPayload(
            meta=AuthorizationPolicyMeta(
                name=f"test-auth-policy-update-{timestamp}-updated",
                description="Updated description",
            )
        )

        updated = authorization_policy.update_authorization_policy(
            self.client,
            self.namespace,
            created.uuid,
            update_payload,
            "meta.name,meta.description",
        )

        assert updated is not None, "Update should succeed"
        assert updated.meta.name == update_payload.meta.name, "Name should be updated"
        assert updated.meta.description == update_payload.meta.description, (
            "Description should be updated"
        )
        print(f"Updated policy name: {updated.meta.name}")

    @pytest.mark.writes
    def test_authorization_policy_delete(self) -> None:
        """Test DELETE authorization policy operation.

        Local-only: requires create (and delete) permissions (403 in CI).
        """
        import time

        from endorlabs.exceptions import NotFoundError

        print("\n=== TESTING AUTHORIZATION POLICY DELETE ===")

        # First create a policy to delete
        timestamp = int(time.time())
        create_payload = CreateAuthorizationPolicyPayload(
            meta=AuthorizationPolicyMeta(
                name=f"test-auth-policy-delete-{timestamp}",
                description="Test policy for delete testing",
            ),
            spec=AuthorizationPolicySpec(
                clause=["test@endor.ai"],
                target_namespaces=[self.namespace],
                propagate=False,
                permissions=AuthorizationPolicyPermissions(
                    roles=[SystemRole.READ_ONLY.value]
                ),
            ),
            propagate=False,
        )

        created = authorization_policy.create_authorization_policy(
            self.client, self.namespace, create_payload
        )
        if not created:
            pytest.skip("Failed to create policy for delete test")

        policy_uuid = created.uuid
        # Allow API eventual consistency before delete
        time.sleep(2)

        try:
            result = authorization_policy.delete_authorization_policy(
                self.client, self.namespace, policy_uuid
            )
        except NotFoundError:
            pytest.skip(
                "AuthorizationPolicy delete: policy not found (namespace/timing)"
            )

        assert result is True, "Delete should succeed"

        # Verify deleted: get should eventually raise NotFoundError (404)
        # Retry a few times to tolerate backend eventual consistency
        max_attempts = 5
        for attempt in range(max_attempts):
            time.sleep(2)
            try:
                still = authorization_policy.get_authorization_policy(
                    self.client, self.namespace, policy_uuid
                )
                if still is None:
                    break
                if attempt == max_attempts - 1:
                    pytest.fail(
                        "Policy should be deleted (get returned object after "
                        f"{max_attempts} attempts)"
                    )
            except NotFoundError:
                break  # Expected: 404 after delete
        print(f"Deleted policy UUID: {policy_uuid}")

    def test_authorization_policy_filter_by_role(self) -> None:
        """Test filtering authorization policies by system role."""
        print("\n=== TESTING AUTHORIZATION POLICY FILTER BY ROLE ===")

        policies = authorization_policy.list_authorization_policies_by_role(
            self.client, self.namespace, SystemRole.CODE_SCANNER
        )

        assert isinstance(policies, list), "Should return a list"
        print(f"Found {len(policies)} policies with CODE_SCANNER role")

        # Verify all returned policies have the role
        for policy in policies:
            if policy.spec.permissions.roles:
                assert SystemRole.CODE_SCANNER.value in policy.spec.permissions.roles, (
                    "All policies should have CODE_SCANNER role"
                )

    def test_client_recommended_ux_list_authorization_policies(self) -> None:
        """Recommended UX: Client(tenant=...); client.authorization_policies.list()."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.namespace,
            max_retries=2,
            backoff_factor=0.1,
            auth_method="api-key",
        )
        policies = client.authorization_policies.list(max_pages=1)
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
    test_instance = TestAuthorizationPolicy()

    # Manual setup
    from endorlabs.types import ListParameters

    test_instance.client = APIClient(auth_method="api-key")
    test_instance.namespace = os.getenv(
        "ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT
    )
    test_instance.policies = authorization_policy.list_authorization_policies(
        test_instance.client,
        test_instance.namespace,
        list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
        max_pages=conftest.TEST_MAX_PAGES,
    )

    try:
        print("Running authorization policy resource tests...")

        # Run all tests
        test_instance.test_authorization_policy_get_list()
        test_instance.test_authorization_policy_get_by_uuid()
        test_instance.test_authorization_policy_structure_analysis()
        test_instance.test_authorization_policy_filter_by_role()

        # Run CRUD tests
        test_instance.test_authorization_policy_create_with_role()
        test_instance.test_authorization_policy_create_with_resource_permissions()
        test_instance.test_authorization_policy_update()
        test_instance.test_authorization_policy_delete()
        test_instance.test_authorization_policy_full_crud_cycle()

        print("\n[SUCCESS] All authorization policy tests completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        test_instance.teardown_method()
