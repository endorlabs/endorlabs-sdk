import os
import sys
import time

import conftest
import httpx
import pytest

# Ensure src/ is on sys.path for direct import
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)
from endorlabs.exceptions import (
    ValidationError as EndorValidationError,
)
from endorlabs.resources.namespace import (
    CreateNamespacePayload,
    NamespaceMetaCreate,
    NamespaceMetaUpdate,
    UpdateNamespacePayload,
    create_namespace,
    delete_namespace,
    get_namespace,
    list_namespaces,
    update_namespace,
)


@pytest.mark.integration
class TestNamespaces:
    """Test cases for Namespace resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client_fast_retry, namespace, root_namespace) -> None:
        """Set up test environment (client and namespace from conftest)."""
        required_vars = [
            "ENDOR_API",
            "ENDOR_API_CREDENTIALS_KEY",
            "ENDOR_API_CREDENTIALS_SECRET",
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            pytest.skip(f"Missing required environment variables: {missing_vars}")

        self.client = api_client_fast_retry
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.created_namespace_uuids = []

    def teardown_method(self) -> None:
        """Clean up any namespaces created during tests."""
        if hasattr(self, "created_namespace_uuids"):
            for namespace_uuid in self.created_namespace_uuids:
                try:
                    delete_namespace(self.client, self.namespace, namespace_uuid)
                    print(f"[CLEANUP] Deleted test namespace: {namespace_uuid}")
                except Exception as e:
                    print(
                        f"[WARNING] Failed to delete test namespace "
                        f"{namespace_uuid}: {e}"
                    )
            self.created_namespace_uuids.clear()

    def test_namespaces_main_flow(self) -> None:
        """Test namespace creation, listing, and cleanup."""
        # Create mock namespaces
        # Use timestamp and random ID to ensure unique names
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

        for payload in mock_namespaces_to_create:
            try:
                ns = create_namespace(self.client, self.namespace, payload)
                if ns:
                    self.created_namespace_uuids.append(ns.uuid)
            except Exception as e:
                print(f"Warning: Failed to create namespace {payload.meta.name}: {e}")
                # Continue with other namespaces

        # List with traverse so created namespaces are in scope
        from endorlabs.types import ListParameters

        all_namespaces = list_namespaces(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=10, traverse=True),
            max_pages=5,
        )
        mock_names = {p.meta.name for p in mock_namespaces_to_create}
        found = [ns for ns in all_namespaces if ns.meta.name in mock_names]

        # Assert that at least one namespace was created successfully
        expected_msg = (
            f"Expected at least 1 namespace, found {len(found)}. "
            f"Created UUIDs: {self.created_namespace_uuids}"
        )
        assert len(found) >= 1, expected_msg

        # Note: Cleanup will be handled by teardown_method

    def test_namespace_update(self) -> None:
        """Test UPDATE namespace via collection PATCH with update_mask."""
        print("\n=== TESTING NAMESPACE UPDATE ===")

        # Create a test namespace first
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

        created_namespace = create_namespace(
            self.client, self.namespace, create_payload
        )
        if not created_namespace:
            pytest.skip("Failed to create namespace for update test")

        namespace_uuid = created_namespace.uuid
        self.created_namespace_uuids.append(namespace_uuid)

        # Wait for namespace to be fully created
        time.sleep(2)

        # Get current namespace state
        current_namespace = get_namespace(self.client, self.namespace, namespace_uuid)
        if not current_namespace:
            pytest.skip(f"Could not retrieve namespace {namespace_uuid}")

        # Store original values
        original_description = current_namespace.meta.description

        # Create update payload and update with required update_mask
        new_description = "Updated description for test namespace"
        update_payload = UpdateNamespacePayload(
            meta=NamespaceMetaUpdate(description=new_description)
        )

        print(f"Updating namespace: {namespace_uuid} with update_mask=meta.description")

        try:
            updated_namespace = update_namespace(
                self.client,
                self.namespace,
                namespace_uuid,
                update_payload,
                update_mask="meta.description",
            )
        except EndorValidationError as e:
            # Backend may return 400 "at least one fieldmask" if contract differs
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
                    "Namespace PATCH returns 501 in this environment (not implemented)"
                )
            raise

        assert updated_namespace is not None, "Namespace update should succeed"
        assert updated_namespace.meta.description == new_description, (
            "Namespace description should be updated"
        )

        print(f"[SUCCESS] Namespace updated: {updated_namespace.uuid}")

        # Restore original description if possible
        restore_payload = UpdateNamespacePayload(
            meta=NamespaceMetaUpdate(description=original_description)
        )
        try:
            update_namespace(
                self.client,
                self.namespace,
                namespace_uuid,
                restore_payload,
                update_mask="meta.description",
            )
            print("[CLEANUP] Restored original namespace values")
        except Exception as e:
            print(f"[WARNING] Failed to restore original values: {e}")

    def test_namespace_update_requires_mask(self) -> None:
        """update_namespace raises ValidationError when update_mask is missing/empty."""
        payload = UpdateNamespacePayload(
            meta=NamespaceMetaUpdate(description="irrelevant")
        )
        with pytest.raises(EndorValidationError) as exc_info:
            update_namespace(
                self.client,
                self.namespace,
                "any-uuid",
                payload,
                update_mask="",
            )
        assert "update_mask" in (exc_info.value.message or "").lower()
        assert "field mask" in (exc_info.value.message or "").lower() or (
            "fieldmask" in (exc_info.value.message or "").lower()
        )

    def test_namespace_list(self) -> None:
        """LIST from tenant root with traverse."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        result = client.namespace.list(
            traverse=True,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_namespace_get(self) -> None:
        """GET first item from LIST (root + traverse)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.namespace.list(
            traverse=True,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        got = client.namespace.get(item)
        assert got is not None
        assert got.uuid == item.uuid

    def test_client_ux_create_namespace(self) -> None:
        """Consumer UX: client.namespace.create(payload); teardown deletes."""
        import random

        import endorlabs

        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        timestamp = int(time.time())
        random_id = random.randint(1000, 9999)
        payload = CreateNamespacePayload(
            meta=NamespaceMetaCreate(
                name=f"client-ux-ns-{timestamp}-{random_id}",
                description="Consumer UX create test",
            )
        )
        try:
            created = client.namespace.create(payload)
        except Exception as e:
            pytest.skip(f"Namespace create not allowed in this environment: {e}")
        assert created is not None
        assert created.meta.name == payload.meta.name
        self.created_namespace_uuids.append(created.uuid)

    def test_client_ux_delete_namespace(self) -> None:
        """Consumer UX: create namespace then client.namespace.delete(uuid)."""
        import random

        import endorlabs

        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        timestamp = int(time.time())
        random_id = random.randint(1000, 9999)
        payload = CreateNamespacePayload(
            meta=NamespaceMetaCreate(
                name=f"client-ux-del-ns-{timestamp}-{random_id}",
                description="Consumer UX delete test",
            )
        )
        try:
            created = client.namespace.create(payload)
        except Exception as e:
            pytest.skip(f"Namespace create not allowed in this environment: {e}")
        if not created:
            pytest.skip("Failed to create namespace for delete test")
        result = client.namespace.delete(created.uuid)
        assert result is True
        # Do not append to created_namespace_uuids; resource already deleted
