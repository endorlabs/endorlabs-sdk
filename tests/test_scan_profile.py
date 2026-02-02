"""Test cases for ScanProfile resource operations.

Tests CRUD operations for ScanProfile resources. ScanProfiles define scan
configuration including toolchains and scan parameters.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import conftest

from endorlabs.resources import scan_profile
from endorlabs.resources.scan_profile import (
    CreateScanProfilePayload,
    ScanProfileMetaCreate,
    ScanProfileMetaUpdate,
    ScanProfileSpecCreate,
    UpdateScanProfilePayload,
)
from endorlabs.types import ListParameters


@pytest.mark.integration
class TestScanProfile:
    """Test cases for ScanProfile resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace, root_namespace) -> None:
        """Fast setup: client and namespace from conftest."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.parent_namespace = root_namespace
        self.created_scan_profile_uuids = []

    def teardown_method(self) -> None:
        """Clean up any scan profiles created during tests."""
        if hasattr(self, "created_scan_profile_uuids"):
            for scan_profile_uuid in self.created_scan_profile_uuids:
                try:
                    scan_profile.delete_scan_profile(
                        self.client, self.parent_namespace, scan_profile_uuid
                    )
                    print(f"[CLEANUP] Deleted test scan profile: {scan_profile_uuid}")
                except Exception as e:
                    print(
                        f"[WARNING] Failed to delete test scan profile "
                        f"{scan_profile_uuid}: {e}"
                    )
            self.created_scan_profile_uuids.clear()
        client = getattr(self, "client", None)
        if client is not None and callable(getattr(client, "close", None)):
            client.close()

    @pytest.fixture
    def sample_scan_profile(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Only fetches 1 item for fast setup. Tests that need sample data should
        request this fixture explicitly.
        """
        results = scan_profile.list_scan_profiles(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    def test_scan_profile_list(self) -> None:
        """LIST from tenant root with traverse."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        result = client.scan_profile.list(
            traverse=True,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_scan_profile_get(self) -> None:
        """GET first item from LIST (root + traverse)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.scan_profile.list(
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
        got = client.scan_profile.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    def test_scan_profile_advanced_filtering(self) -> None:
        """Test advanced filtering capabilities."""
        print("\n=== TESTING SCAN PROFILE FILTERING ===")
        import conftest

        # Test filtering by is_default
        default_profiles = scan_profile.list_scan_profiles(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(
                filter="spec.is_default==true",
                page_size=conftest.TEST_PAGE_SIZE,
            ),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(default_profiles, list), (
            "Should return a list of scan profiles"
        )
        print(f"Found {len(default_profiles)} default scan profiles")

        # Test field masking
        masked_profiles = scan_profile.list_scan_profiles(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(
                mask="meta.name,spec.is_default",
                page_size=conftest.TEST_PAGE_SIZE,
            ),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(masked_profiles, list), (
            "Should return a list of masked scan profiles"
        )
        if masked_profiles:
            profile = masked_profiles[0]
            # Should have masked fields
            assert hasattr(profile, "meta")
            assert hasattr(profile, "spec")
            print(f"Masked profile: {profile.meta.name if profile.meta else 'N/A'}")

    def test_scan_profile_error_handling(self) -> None:
        """Test error handling for invalid UUID."""
        # Test with invalid UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endorlabs.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            scan_profile.get_scan_profile(
                self.client, self.parent_namespace, "invalid-uuid"
            )
        assert exc_info.value.resource_uuid == "invalid-uuid"
        assert exc_info.value.operation == "get"
        assert exc_info.value.status_code == 400

    @pytest.mark.writes
    def test_client_ux_create_scan_profile(self) -> None:
        """Consumer UX: client.scan_profile.create(payload); teardown deletes."""
        import time

        import endorlabs

        client = endorlabs.Client(
            tenant=self.parent_namespace,
            api_client=self.client,
        )
        payload = CreateScanProfilePayload(
            meta=ScanProfileMetaCreate(
                name=f"client-ux-profile-{int(time.time())}",
                description="Consumer UX create test",
            ),
            spec=ScanProfileSpecCreate(is_default=False),
            propagate=False,
        )
        try:
            created = client.scan_profile.create(payload)
        except Exception as e:
            pytest.skip(f"Scan profile create not allowed in this environment: {e}")
        assert created is not None
        assert created.meta.name == payload.meta.name
        self.created_scan_profile_uuids.append(created.uuid)

    @pytest.mark.writes
    def test_client_ux_update_scan_profile(self) -> None:
        """Consumer UX: create then get then update then revert then delete."""
        import time

        import endorlabs

        client = endorlabs.Client(
            tenant=self.parent_namespace,
            api_client=self.client,
        )
        payload = CreateScanProfilePayload(
            meta=ScanProfileMetaCreate(
                name=f"client-ux-update-{int(time.time())}",
                description="Original description",
            ),
            spec=ScanProfileSpecCreate(is_default=False),
            propagate=False,
        )
        try:
            created = client.scan_profile.create(payload)
        except Exception as e:
            pytest.skip(f"Scan profile create not allowed in this environment: {e}")
        if not created:
            pytest.skip("Failed to create scan profile for update test")
        self.created_scan_profile_uuids.append(created.uuid)
        current = client.scan_profile.get(created.uuid, namespace=self.parent_namespace)
        if not current:
            pytest.skip(f"Could not retrieve scan profile {created.uuid}")
        original_description = getattr(current.meta, "description", None) or ""
        update_payload = UpdateScanProfilePayload(
            meta=ScanProfileMetaUpdate(description="Updated by client-ux")
        )
        try:
            updated = client.scan_profile.update(
                created.uuid,
                update_payload,
                update_mask="meta.description",
                namespace=self.parent_namespace,
            )
        except Exception as e:
            pytest.skip(f"Scan profile update not allowed in this environment: {e}")
        assert updated is not None
        restore_payload = UpdateScanProfilePayload(
            meta=ScanProfileMetaUpdate(description=original_description)
        )
        try:
            client.scan_profile.update(
                created.uuid,
                restore_payload,
                update_mask="meta.description",
                namespace=self.parent_namespace,
            )
        except Exception as e:
            print(f"[WARNING] Failed to restore original scan profile values: {e}")

    @pytest.mark.writes
    def test_client_ux_delete_scan_profile(self) -> None:
        """Consumer UX: create then client.scan_profile.delete(uuid)."""
        import time

        import endorlabs

        client = endorlabs.Client(
            tenant=self.parent_namespace,
            api_client=self.client,
        )
        payload = CreateScanProfilePayload(
            meta=ScanProfileMetaCreate(
                name=f"client-ux-del-{int(time.time())}",
                description="Consumer UX delete test",
            ),
            spec=ScanProfileSpecCreate(is_default=False),
            propagate=False,
        )
        try:
            created = client.scan_profile.create(payload)
        except Exception as e:
            pytest.skip(f"Scan profile create not allowed in this environment: {e}")
        if not created:
            pytest.skip("Failed to create scan profile for delete test")
        result = client.scan_profile.delete(created.uuid)
        assert result is True
        # Do not append to created_scan_profile_uuids; resource already deleted
