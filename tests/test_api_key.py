"""Test cases for APIKey resource operations.

Tests list, get, create+delete (GC), and Client-recommended UX for APIKey resources.
Aligns with test-driven-development.mdc and resource-implementation.md.
"""

import os
import sys
from datetime import UTC, datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import conftest

from endorlabs.api_client import APIClient
from endorlabs.resources import api_key
from endorlabs.resources.api_key import (
    APIKeyMeta,
    APIKeyPermissions,
    APIKeySpec,
    CreateAPIKeyPayload,
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
        self.created_api_key_uuids: list[str] = []

    def teardown_method(self) -> None:
        """Clean up any API keys created during tests (GC)."""
        if hasattr(self, "created_api_key_uuids"):
            for key_uuid in self.created_api_key_uuids:
                try:
                    api_key.delete_api_key(self.client, self.namespace, key_uuid)
                except Exception as e:
                    print(f"[WARNING] Failed to delete API key {key_uuid}: {e}")
            self.created_api_key_uuids.clear()

    def test_api_key_list(self) -> None:
        """LIST from tenant root with traverse (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        result = client.api_key.list(
            traverse=True,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_api_key_get(self) -> None:
        """GET first item from LIST (root + traverse) (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.api_key.list(
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
        got = client.api_key.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    def test_client_ux_create_api_key(self) -> None:
        """Consumer UX: client.api_key.create(payload); teardown deletes."""
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
            created = client.api_key.create(payload)
        except Exception as e:
            pytest.skip(f"API key create not allowed in this environment: {e}")
        try:
            assert created is not None
            assert created.uuid
            self.created_api_key_uuids.append(created.uuid)
        finally:
            if created is not None:  # type: ignore[reportUnnecessaryComparison]
                try:
                    api_key.delete_api_key(self.client, self.namespace, created.uuid)
                except Exception as e:
                    print(f"[WARNING] Cleanup failed for {created.uuid}: {e}")

    def test_client_ux_delete_api_key(self) -> None:
        """Consumer UX: create then client.api_key.delete(uuid)."""
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
            created = client.api_key.create(payload)
        except Exception as e:
            pytest.skip(f"API key create not allowed in this environment: {e}")
        if not created:
            pytest.skip("Failed to create API key for delete test")
        result = client.api_key.delete(created.uuid)
        assert result is True

    def test_api_key_update_raises_not_implemented(self) -> None:
        """When update_fn is None, client.api_key.update raises NotImplementedError."""
        from unittest.mock import Mock

        import endorlabs

        mock = Mock(spec=APIClient)
        client = endorlabs.Client(
            api_client=mock,
            tenant=conftest.TEST_NAMESPACE_DEFAULT,
        )
        with pytest.raises(NotImplementedError, match="does not support update"):
            client.api_key.update("dummy-uuid", {}, update_mask="meta.description")
