"""Test cases for APIKey resource operations.

Tests list, get, create+delete (GC), and Client (facade) UX for APIKey resources.
Aligns with docs/contributing/integration-resource-tests.md.
"""

from datetime import UTC, datetime, timedelta

import pytest

import endorlabs
from endorlabs.api_client import APIClient
from endorlabs.resources.api_key import (
    APIKeyMeta,
    APIKeyPermissions,
    APIKeySpec,
    CreateAPIKeyPayload,
)
from tests.conftest import (
    TEST_MAX_PAGES,
    TEST_NAMESPACE_DEFAULT,
)


@pytest.mark.integration
class TestAPIKey:
    """Test cases for APIKey resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client_fast_retry, namespace, root_namespace) -> None:
        """Set up test environment (client and namespace from conftest)."""
        self.client = api_client_fast_retry
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.endor_client = endorlabs.Client(
            tenant=namespace, api_client=api_client_fast_retry
        )
        self.endor_root_client = endorlabs.Client(
            tenant=root_namespace, api_client=api_client_fast_retry
        )
        self.created_api_key_uuids: list[str] = []

    def teardown_method(self) -> None:
        """Clean up any API keys created during tests (GC)."""
        if hasattr(self, "created_api_key_uuids"):
            for key_uuid in self.created_api_key_uuids:
                try:
                    self.endor_client.APIKey.delete(key_uuid)
                except Exception as e:
                    print(f"[WARNING] Failed to delete API key {key_uuid}: {e}")
            self.created_api_key_uuids.clear()

    def test_api_key_list(self) -> None:
        """LIST in namespace (registry-based)."""
        result = self.endor_client.APIKey.list(
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, list)

    def test_api_key_get(self) -> None:
        """GET first item from LIST in namespace (registry-based)."""
        items = self.endor_client.APIKey.list(
            max_pages=TEST_MAX_PAGES,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        got = self.endor_client.APIKey.get(item)
        assert got is not None
        assert got.uuid == item.uuid

    def test_client_ux_create_api_key(self) -> None:
        """Consumer UX: client.APIKey.create(payload); teardown deletes."""
        import endorlabs

        expiration = (datetime.now(UTC) + timedelta(days=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        payload = CreateAPIKeyPayload(
            meta=APIKeyMeta(
                name="test-client-ux-api-key",
                description="Consumer UX create test",
            ),
            spec=APIKeySpec(
                permissions=APIKeyPermissions(roles=["SYSTEM_ROLE_READ_ONLY"]),
                expiration_time=expiration,
            ),
            propagate=False,
        )
        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        created = None
        try:
            created = client.APIKey.create(payload)
        except Exception as e:
            pytest.skip(f"API key create not allowed in this environment: {e}")
        try:
            assert created is not None
            assert created.uuid
            self.created_api_key_uuids.append(created.uuid)
        finally:
            if created is not None:
                try:
                    self.endor_client.APIKey.delete(created.uuid)
                except Exception as e:
                    print(f"[WARNING] Cleanup failed for {created.uuid}: {e}")

    def test_client_ux_delete_api_key(self) -> None:
        """Consumer UX: create then client.APIKey.delete(uuid)."""
        import endorlabs

        expiration = (datetime.now(UTC) + timedelta(days=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        payload = CreateAPIKeyPayload(
            meta=APIKeyMeta(
                name="test-client-ux-api-key-del",
                description="Consumer UX delete test",
            ),
            spec=APIKeySpec(
                permissions=APIKeyPermissions(roles=["SYSTEM_ROLE_READ_ONLY"]),
                expiration_time=expiration,
            ),
            propagate=False,
        )
        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        try:
            created = client.APIKey.create(payload)
        except Exception as e:
            pytest.skip(f"API key create not allowed in this environment: {e}")
        if not created:
            pytest.skip("Failed to create API key for delete test")
        result = client.APIKey.delete(created.uuid)
        assert result is True

    def test_api_key_update_raises_not_implemented(self) -> None:
        """When update_fn is None, client.APIKey.update raises NotImplementedError."""
        from unittest.mock import Mock

        import endorlabs

        mock = Mock(spec=APIClient)
        client = endorlabs.Client(
            api_client=mock,
            tenant=TEST_NAMESPACE_DEFAULT,
        )
        with pytest.raises(NotImplementedError, match="does not support update"):
            client.APIKey.update("dummy-uuid", {}, update_mask="meta.description")
