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
from endorlabs.types import ListParameters


@pytest.mark.integration
class TestAPIKey:
    """Test cases for APIKey resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Set up test environment."""
        self.client = APIClient(
            max_retries=2, backoff_factor=0.1, auth_method="api-key"
        )
        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)

        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

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
        """Test GET API keys (list) with pagination limits."""
        keys = api_key.list_api_keys(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=2,
        )
        assert isinstance(keys, list)

    def test_api_key_get_by_uuid(self) -> None:
        """Test GET API key by UUID when at least one key exists."""
        keys = api_key.list_api_keys(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=1),
            max_pages=1,
        )
        if not keys:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

        key = api_key.get_api_key(self.client, self.namespace, keys[0].uuid)
        assert key is not None
        assert key.uuid == keys[0].uuid

    def test_api_key_create_and_delete_gc(self) -> None:
        """Create an API key then delete it (garbage collection)."""
        expiration = (datetime.now(UTC) + timedelta(days=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        payload = CreateAPIKeyPayload(
            meta=APIKeyMeta(
                name="test-cockpit-api-key-gc",
                description="Temporary key for test GC",
            ),
            spec=APIKeySpec(
                permissions=APIKeyPermissions(roles=["SYSTEM_ROLE_READ_ONLY"]),
                expiration_time=expiration,
            ),
            propagate=False,
        )
        created = api_key.create_api_key(self.client, self.namespace, payload)
        assert created is not None
        assert created.uuid
        self.created_api_key_uuids.append(created.uuid)

        deleted = api_key.delete_api_key(self.client, self.namespace, created.uuid)
        assert deleted is True
        self.created_api_key_uuids.remove(created.uuid)

    def test_client_recommended_ux_list_api_keys(self) -> None:
        """Recommended UX: Client(tenant=...); client.api_keys.list()."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.namespace,
            max_retries=2,
            backoff_factor=0.1,
            auth_method="api-key",
        )
        keys = client.api_keys.list(max_pages=1)
        assert isinstance(keys, list)
