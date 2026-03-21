"""Test cases for AuthorizationPolicy resource operations.

Tests full CRUD operations for AuthorizationPolicy resources using various
system roles and permission configurations.
Includes validation, filtering, and comprehensive CRUD testing with live data.
"""

import time

import pytest

import endorlabs
from endorlabs.resources import authorization_policy
from endorlabs.resources.authorization_policy import (
    AuthorizationPolicyMeta,
    AuthorizationPolicyPermissions,
    AuthorizationPolicySpec,
    CreateAuthorizationPolicyPayload,
    SystemRole,
    UpdateAuthorizationPolicyPayload,
)
from tests.conftest import (
    TEST_MAX_PAGES_TRAVERSE,
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
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.endor_root_client = endorlabs.Client(
            tenant=root_namespace, api_client=api_client
        )
        self.created_policy_uuids = []

    def teardown_method(self) -> None:
        """Clean up any policies created during tests."""
        if hasattr(self, "created_policy_uuids"):
            for policy_uuid in self.created_policy_uuids:
                try:
                    self.endor_client.AuthorizationPolicy.delete(policy_uuid)
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
        result = client.AuthorizationPolicy.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_authorization_policy_get(self) -> None:
        """GET first item from LIST (root + traverse)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.AuthorizationPolicy.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.root_namespace
        )
        got = client.AuthorizationPolicy.get(item.uuid, namespace=ns)
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
            created = client.AuthorizationPolicy.create(payload)
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
                    self.endor_client.AuthorizationPolicy.delete(created.uuid)
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
            created = client.AuthorizationPolicy.create(create_payload)
        except Exception as e:
            pytest.skip(
                f"Authorization policy create not allowed in this environment: {e}"
            )
        try:
            if not created:
                pytest.skip("Failed to create authorization policy for update test")
            self.created_policy_uuids.append(created.uuid)
            current = client.AuthorizationPolicy.get(
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
                updated = client.AuthorizationPolicy.update(
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
                client.AuthorizationPolicy.update(
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
                    self.endor_client.AuthorizationPolicy.delete(created.uuid)
                except Exception as e:
                    print(f"[WARNING] Cleanup failed for {created.uuid}: {e}")

    @pytest.mark.writes
    def test_client_ux_delete_authorization_policy(self) -> None:
        """Consumer UX: create then client.AuthorizationPolicy.delete(uuid)."""
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
            created = client.AuthorizationPolicy.create(payload)
        except Exception as e:
            pytest.skip(
                f"Authorization policy create not allowed in this environment: {e}"
            )
        if not created:
            pytest.skip("Failed to create authorization policy for delete test")
        result = client.AuthorizationPolicy.delete(created.uuid)
        assert result is True
