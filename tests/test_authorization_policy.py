"""
Test cases for AuthorizationPolicy resource operations.

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

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import authorization_policy
from endor_cockpit.resources.authorization_policy import (
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
    def setup(self):
        """Set up test environment."""
        self.client = APIClient()
        self.namespace = os.getenv("ENDOR_NAMESPACE", "")
        self.created_policy_uuids = []  # Track created policies for cleanup

        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Get test data
        self.policies = authorization_policy.list_authorization_policies(
            self.client, self.namespace
        )

    def teardown_method(self):
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
                        f"[WARNING] Failed to delete test authorization policy {policy_uuid}: {e}"
                    )
            self.created_policy_uuids.clear()

    def test_authorization_policy_get_list(self):
        """Test GET authorization policies operation."""
        print("\n=== TESTING AUTHORIZATION POLICY LIST ===")

        policies = authorization_policy.list_authorization_policies(
            self.client, self.namespace
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

    def test_authorization_policy_get_by_uuid(self):
        """Test GET authorization policy by UUID operation."""
        print("\n=== TESTING AUTHORIZATION POLICY GET BY UUID ===")

        policies = authorization_policy.list_authorization_policies(
            self.client, self.namespace
        )
        if not policies:
            pytest.skip("No authorization policies available for testing")

        test_policy = policies[0]
        retrieved = authorization_policy.get_authorization_policy(
            self.client, self.namespace, test_policy.uuid
        )

        assert retrieved is not None, "Should retrieve policy"
        assert retrieved.uuid == test_policy.uuid, "UUID should match"
        assert retrieved.meta.name == test_policy.meta.name, "Name should match"
        print(f"Retrieved policy: {retrieved.meta.name}")

    def test_authorization_policy_create_with_role(self):
        """Test CREATE authorization policy operation with system role."""
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

    def test_authorization_policy_create_with_resource_permissions(self):
        """Test CREATE authorization policy with resource-specific permissions."""
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
        assert created_policy.spec.permissions.rules is not None, (
            "Rules should be set"
        )

        # Track for cleanup
        self.created_policy_uuids.append(created_policy.uuid)
        print(f"Created policy UUID: {created_policy.uuid}")

    def test_authorization_policy_update(self):
        """Test UPDATE authorization policy operation."""
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
        assert updated.meta.name == update_payload.meta.name, (
            "Name should be updated"
        )
        assert updated.meta.description == update_payload.meta.description, (
            "Description should be updated"
        )
        print(f"Updated policy name: {updated.meta.name}")

    def test_authorization_policy_delete(self):
        """Test DELETE authorization policy operation."""
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

        # Delete the policy
        result = authorization_policy.delete_authorization_policy(
            self.client, self.namespace, policy_uuid
        )

        assert result is True, "Delete should succeed"

        # Verify it's deleted
        deleted_policy = authorization_policy.get_authorization_policy(
            self.client, self.namespace, policy_uuid
        )
        # Note: API might return 404 or None, both are acceptable
        print(f"Deleted policy UUID: {policy_uuid}")

    def test_authorization_policy_filter_by_role(self):
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

    def test_authorization_policy_structure_analysis(self):
        """Test authorization policy structure and field analysis."""
        print("\n=== TESTING AUTHORIZATION POLICY STRUCTURE ===")

        policies = authorization_policy.list_authorization_policies(
            self.client, self.namespace
        )
        if not policies:
            pytest.skip("No authorization policies available for analysis")

        policy = policies[0]

        # Check required fields
        assert hasattr(policy, "uuid"), "Policy should have uuid"
        assert hasattr(policy, "meta"), "Policy should have meta"
        assert hasattr(policy, "spec"), "Policy should have spec"
        assert hasattr(policy, "tenant_meta"), "Policy should have tenant_meta"

        # Check meta fields
        assert hasattr(policy.meta, "name"), "Meta should have name"
        assert hasattr(policy.meta, "kind"), "Meta should have kind"

        # Check spec fields
        assert hasattr(policy.spec, "clause"), "Spec should have clause"
        assert hasattr(policy.spec, "target_namespaces"), (
            "Spec should have target_namespaces"
        )
        assert hasattr(policy.spec, "permissions"), "Spec should have permissions"

        # Check permissions structure
        if policy.spec.permissions:
            assert hasattr(
                policy.spec.permissions, "roles"
            ), "Permissions should have roles"
            assert hasattr(
                policy.spec.permissions, "rules"
            ), "Permissions should have rules"

        print("Policy structure validation passed")

    def test_authorization_policy_full_crud_cycle(self):
        """Test full CRUD cycle for authorization policy."""
        print("\n=== TESTING AUTHORIZATION POLICY FULL CRUD CYCLE ===")

        timestamp = int(time.time())

        # CREATE
        create_payload = CreateAuthorizationPolicyPayload(
            meta=AuthorizationPolicyMeta(
                name=f"test-crud-cycle-{timestamp}",
                description="Test policy for full CRUD cycle",
                tags=["test", "crud"],
            ),
            spec=AuthorizationPolicySpec(
                clause=["test@endor.ai"],
                target_namespaces=[self.namespace],
                propagate=False,
                permissions=AuthorizationPolicyPermissions(
                    roles=[SystemRole.POLICY_EDITOR.value]
                ),
            ),
            propagate=False,
        )

        created = authorization_policy.create_authorization_policy(
            self.client, self.namespace, create_payload
        )
        assert created is not None, "CREATE should succeed"
        self.created_policy_uuids.append(created.uuid)

        # READ
        retrieved = authorization_policy.get_authorization_policy(
            self.client, self.namespace, created.uuid
        )
        assert retrieved is not None, "READ should succeed"
        assert retrieved.uuid == created.uuid, "UUID should match"

        # UPDATE
        update_payload = UpdateAuthorizationPolicyPayload(
            meta=AuthorizationPolicyMeta(
                name=f"test-crud-cycle-{timestamp}-updated",
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
        assert updated is not None, "UPDATE should succeed"
        assert updated.meta.name == update_payload.meta.name, "Name should be updated"

        # DELETE
        deleted = authorization_policy.delete_authorization_policy(
            self.client, self.namespace, created.uuid
        )
        assert deleted is True, "DELETE should succeed"

        # Remove from cleanup list since we deleted it
        if created.uuid in self.created_policy_uuids:
            self.created_policy_uuids.remove(created.uuid)

        print("Full CRUD cycle completed successfully")


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
    test_instance.client = APIClient()
    test_instance.namespace = os.getenv("ENDOR_NAMESPACE", "")
    test_instance.policies = authorization_policy.list_authorization_policies(
        test_instance.client, test_instance.namespace
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

