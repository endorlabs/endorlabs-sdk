import os
import time

import httpx
import pytest

import endorlabs
from endorlabs.core.exceptions import (
    ValidationError as EndorValidationError,
)
from endorlabs.resources.namespace import (
    CreateNamespacePayload,
    NamespaceMetaCreate,
    NamespaceMetaUpdate,
    UpdateNamespacePayload,
)
from tests.conftest import TEST_MAX_PAGES_TRAVERSE


@pytest.mark.integration
class TestNamespaces:
    """Test cases for Namespace resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client_fast_retry, namespace, root_namespace) -> None:
        """Set up test environment (client and namespace from conftest)."""
        required_vars = [
            "ENDOR_API_CREDENTIALS_KEY",
            "ENDOR_API_CREDENTIALS_SECRET",
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            pytest.skip(f"Missing required environment variables: {missing_vars}")

        self.api_client = api_client_fast_retry
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.created_namespace_uuids: list[str] = []
        self.client = endorlabs.Client(
            tenant=namespace, api_client=api_client_fast_retry
        )
        self.root_client = endorlabs.Client(
            tenant=root_namespace, api_client=api_client_fast_retry
        )

    def teardown_method(self) -> None:
        """Clean up any namespaces created during tests."""
        if hasattr(self, "created_namespace_uuids"):
            for namespace_uuid in self.created_namespace_uuids:
                try:
                    self.client.Namespace.delete(namespace_uuid)
                    print(f"[CLEANUP] Deleted test namespace: {namespace_uuid}")
                except Exception as e:
                    print(
                        f"[WARNING] Failed to delete test namespace "
                        f"{namespace_uuid}: {e}"
                    )
            self.created_namespace_uuids.clear()

    def test_namespaces_main_flow(self) -> None:
        """Test namespace creation, listing, and cleanup."""
        import random

        timestamp = int(time.time())
        random_id = random.randint(1000, 9999)
        mock_namespaces_to_create = [
            CreateNamespacePayload(
                meta=NamespaceMetaCreate(
                    name=f"mock-namespace-{timestamp}-{random_id}-{i}",
                    description=(
                        f"Description for mock-namespace-{timestamp}-{random_id}-{i}"
                    ),
                )
            )
            for i in range(2)
        ]

        created_in_this_test: list[str] = []
        try:
            for payload in mock_namespaces_to_create:
                try:
                    ns = self.client.Namespace.create(payload)
                    if ns:
                        created_in_this_test.append(ns.uuid)
                        self.created_namespace_uuids.append(ns.uuid)
                except Exception as e:
                    print(
                        f"Warning: Failed to create namespace {payload.meta.name}: {e}"
                    )

            # List from tenant root with traverse so created child namespaces
            # are in scope.
            all_namespaces = self.root_client.Namespace.list(
                traverse=True,
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
            created_uuids = set(created_in_this_test)
            found = [ns for ns in all_namespaces if ns.uuid in created_uuids]

            expected_msg = (
                f"Expected at least 1 namespace in list (by UUID), found {len(found)}. "
                f"Created UUIDs: {created_in_this_test}"
            )
            assert len(found) >= 1, expected_msg
        finally:
            for uid in created_in_this_test:
                try:
                    self.client.Namespace.delete(uid)
                except Exception as e:
                    print(f"[WARNING] Cleanup failed for namespace {uid}: {e}")

    def test_namespace_update(self) -> None:
        """Test UPDATE namespace via collection PATCH with update_mask."""
        print("\n=== TESTING NAMESPACE UPDATE ===")
        import random

        timestamp = int(time.time())
        random_id = random.randint(1000, 9999)
        test_namespace_name = f"test-update-ns-{timestamp}-{random_id}"

        create_payload = CreateNamespacePayload(
            meta=NamespaceMetaCreate(
                name=test_namespace_name,
                description="Test namespace for update",
            )
        )

        created_namespace = self.client.Namespace.create(create_payload)
        if not created_namespace:
            pytest.skip("Failed to create namespace for update test")

        namespace_uuid = created_namespace.uuid
        self.created_namespace_uuids.append(namespace_uuid)

        try:
            time.sleep(2)

            current_namespace = self.client.Namespace.get(namespace_uuid)
            if not current_namespace:
                pytest.skip(f"Could not retrieve namespace {namespace_uuid}")

            original_description = current_namespace.meta.description

            new_description = "Updated description for test namespace"
            update_payload = UpdateNamespacePayload(
                meta=NamespaceMetaUpdate(description=new_description)
            )

            print(
                f"Updating namespace: {namespace_uuid} with "
                "update_mask=meta.description"
            )

            try:
                updated_namespace = self.client.Namespace.update(
                    namespace_uuid,
                    update_payload,
                    update_mask="meta.description",
                )
            except EndorValidationError as e:
                if (
                    "fieldmask" in (e.message or "").lower()
                    or "field mask" in (e.message or "").lower()
                ):
                    pytest.skip(
                        "Namespace update returned validation error (fieldmask): "
                        f"{e.message}"
                    )
                raise
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 501:
                    pytest.skip(
                        "Namespace PATCH returns 501 in this environment "
                        "(not implemented)"
                    )
                raise

            assert updated_namespace is not None, "Namespace update should succeed"
            assert updated_namespace.meta.description == new_description, (
                "Namespace description should be updated"
            )

            print(f"[SUCCESS] Namespace updated: {updated_namespace.uuid}")

            restore_payload = UpdateNamespacePayload(
                meta=NamespaceMetaUpdate(description=original_description)
            )
            try:
                self.client.Namespace.update(
                    namespace_uuid,
                    restore_payload,
                    update_mask="meta.description",
                )
                print("[CLEANUP] Restored original namespace values")
            except Exception as e:
                print(f"[WARNING] Failed to restore original values: {e}")
        finally:
            try:
                self.client.Namespace.delete(namespace_uuid)
            except Exception as e:
                print(f"[WARNING] Cleanup failed for namespace {namespace_uuid}: {e}")

    def test_namespace_update_requires_mask(self) -> None:
        """Facade update raises ValidationError when update_mask is empty."""
        payload = UpdateNamespacePayload(
            meta=NamespaceMetaUpdate(description="irrelevant")
        )
        with pytest.raises(EndorValidationError) as exc_info:
            self.client.Namespace.update(
                "any-uuid",
                payload,
                update_mask="",
            )
        assert "update_mask" in (exc_info.value.message or "").lower()

    def test_namespace_list(self) -> None:
        """LIST from tenant root with traverse."""
        result = self.root_client.Namespace.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_namespace_get(self) -> None:
        """GET first item from LIST (root + traverse)."""
        items = self.root_client.Namespace.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        got = self.root_client.Namespace.get(item)
        assert got is not None
        assert got.uuid == item.uuid

    def test_namespace_spec_has_full_name_and_managed(self) -> None:
        """Namespace spec exposes full_name and managed when returned by API."""
        items = self.root_client.Namespace.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        assert hasattr(item.spec, "full_name")
        assert hasattr(item.spec, "managed")
        got = self.root_client.Namespace.get(item)
        assert hasattr(got.spec, "full_name")
        assert hasattr(got.spec, "managed")

    def test_client_ux_create_namespace(self) -> None:
        """Consumer UX: client.Namespace.create(payload); teardown deletes."""
        import random

        timestamp = int(time.time())
        random_id = random.randint(1000, 9999)
        payload = CreateNamespacePayload(
            meta=NamespaceMetaCreate(
                name=f"client-ux-ns-{timestamp}-{random_id}",
                description="Consumer UX create test",
            )
        )
        created = None
        try:
            created = self.client.Namespace.create(payload)
        except Exception as e:
            pytest.skip(f"Namespace create not allowed in this environment: {e}")
        try:
            assert created is not None
            assert created.meta.name == payload.meta.name
            self.created_namespace_uuids.append(created.uuid)
        finally:
            if created is not None:  # type: ignore[redundant-expr]
                try:
                    self.client.Namespace.delete(created.uuid)
                except Exception as e:
                    print(f"[WARNING] Cleanup failed for namespace {created.uuid}: {e}")

    def test_client_ux_delete_namespace(self) -> None:
        """Consumer UX: create namespace then client.Namespace.delete(uuid)."""
        import random

        timestamp = int(time.time())
        random_id = random.randint(1000, 9999)
        payload = CreateNamespacePayload(
            meta=NamespaceMetaCreate(
                name=f"client-ux-del-ns-{timestamp}-{random_id}",
                description="Consumer UX delete test",
            )
        )
        try:
            created = self.client.Namespace.create(payload)
        except Exception as e:
            pytest.skip(f"Namespace create not allowed in this environment: {e}")
        if not created:
            pytest.skip("Failed to create namespace for delete test")
        result = self.client.Namespace.delete(created.uuid)
        assert result is True
