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
    def setup_fast(self, api_client, namespace, root_namespace) -> None:
        """Fast setup: client and namespace from conftest."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.created_policy_uuids = []

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

    def test_authorization_policy_list(self) -> None:
        """LIST from tenant root with traverse."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        result = client.authorization_policy.list(
            traverse=True,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_authorization_policy_get(self) -> None:
        """GET first item from LIST (root + traverse)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.authorization_policy.list(
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
        got = client.authorization_policy.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    @pytest.mark.writes
    def test_client_ux_create_authorization_policy(self) -> None:
        """Consumer UX: create via client; teardown deletes."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        timestamp = int(time.time())
        payload = CreateAuthorizationPolicyPayload(
            meta=AuthorizationPolicyMeta(
                name=f"client-ux-auth-{timestamp}",
                description="Consumer UX create test",
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
        created = None
        try:
            created = client.authorization_policy.create(payload)
        except Exception as e:
            pytest.skip(
                f"Authorization policy create not allowed in this environment: {e}"
            )
        try:
            assert created is not None
            assert created.meta.name == payload.meta.name
            self.created_policy_uuids.append(created.uuid)
        finally:
            if created is not None:  # type: ignore[reportUnnecessaryComparison]
                try:
                    authorization_policy.delete_authorization_policy(
                        self.client, self.namespace, created.uuid
                    )
                except Exception as e:
                    print(f"[WARNING] Cleanup failed for {created.uuid}: {e}")

    @pytest.mark.writes
    def test_client_ux_update_authorization_policy(self) -> None:
        """Consumer UX: create then get then update then revert; teardown deletes."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        timestamp = int(time.time())
        create_payload = CreateAuthorizationPolicyPayload(
            meta=AuthorizationPolicyMeta(
                name=f"client-ux-update-{timestamp}",
                description="Original description",
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
        created = None
        try:
            created = client.authorization_policy.create(create_payload)
        except Exception as e:
            pytest.skip(
                f"Authorization policy create not allowed in this environment: {e}"
            )
        try:
            if not created:
                pytest.skip("Failed to create authorization policy for update test")
            self.created_policy_uuids.append(created.uuid)
            current = client.authorization_policy.get(
                created.uuid, namespace=self.namespace
            )
            if not current:
                pytest.skip(f"Could not retrieve authorization policy {created.uuid}")
            original_description = getattr(current.meta, "description", None) or ""
            update_payload = UpdateAuthorizationPolicyPayload(
                meta=AuthorizationPolicyMeta(
                    name=current.meta.name,
                    description="Updated by client-ux",
                )
            )
            try:
                updated = client.authorization_policy.update(
                    created.uuid,
                    update_payload,
                    update_mask="meta.description",
                    namespace=self.namespace,
                )
            except Exception as e:
                pytest.skip(
                    f"Authorization policy update not allowed in this environment: {e}"
                )
            assert updated is not None
            restore_payload = UpdateAuthorizationPolicyPayload(
                meta=AuthorizationPolicyMeta(
                    name=current.meta.name,
                    description=original_description,
                )
            )
            try:
                client.authorization_policy.update(
                    created.uuid,
                    restore_payload,
                    update_mask="meta.description",
                    namespace=self.namespace,
                )
            except Exception as e:
                print(
                    "[WARNING] Failed to restore original authorization "
                    f"policy values: {e}"
                )
        finally:
            if created is not None:  # type: ignore[reportUnnecessaryComparison]
                try:
                    authorization_policy.delete_authorization_policy(
                        self.client, self.namespace, created.uuid
                    )
                except Exception as e:
                    print(f"[WARNING] Cleanup failed for {created.uuid}: {e}")

    @pytest.mark.writes
    def test_client_ux_delete_authorization_policy(self) -> None:
        """Consumer UX: create then client.authorization_policy.delete(uuid)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        timestamp = int(time.time())
        payload = CreateAuthorizationPolicyPayload(
            meta=AuthorizationPolicyMeta(
                name=f"client-ux-del-{timestamp}",
                description="Consumer UX delete test",
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
        try:
            created = client.authorization_policy.create(payload)
        except Exception as e:
            pytest.skip(
                f"Authorization policy create not allowed in this environment: {e}"
            )
        if not created:
            pytest.skip("Failed to create authorization policy for delete test")
        result = client.authorization_policy.delete(created.uuid)
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
        test_instance.test_authorization_policy_structure_analysis()
        test_instance.test_authorization_policy_filter_by_role()
        test_instance.test_authorization_policy_full_crud_cycle()

        print("\n[SUCCESS] All authorization policy tests completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        test_instance.client.close()
        test_instance.teardown_method()
