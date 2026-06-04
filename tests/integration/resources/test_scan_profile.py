"""Test cases for ScanProfile resource operations.

Tests CRUD operations for ScanProfile resources. ScanProfiles define scan
configuration including toolchains and scan parameters.
"""

import pytest

import endorlabs
from endorlabs.core.types import ListParameters
from endorlabs.resources.scan_profile import (
    CreateScanProfilePayload,
    ScanProfileMetaCreate,
    ScanProfileMetaUpdate,
    ScanProfileSpecCreate,
    UpdateScanProfilePayload,
)
from tests.conftest import TEST_MAX_PAGES, TEST_PAGE_SIZE


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
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.endor_root_client = endorlabs.Client(
            tenant=root_namespace, api_client=api_client
        )
        self.created_scan_profile_uuids = []

    def teardown_method(self) -> None:
        """Clean up any scan profiles created during tests."""
        if hasattr(self, "created_scan_profile_uuids"):
            for scan_profile_uuid in self.created_scan_profile_uuids:
                try:
                    self.endor_root_client.ScanProfile.delete(scan_profile_uuid)
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
        results = self.endor_root_client.ScanProfile.list(
            list_params=ListParameters(page_size=TEST_PAGE_SIZE),
            max_pages=TEST_MAX_PAGES,
        )
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    def test_scan_profile_list(self) -> None:
        """LIST in namespace."""
        result = self.endor_client.ScanProfile.list(
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, list)

    def test_scan_profile_get(self) -> None:
        """GET first item from LIST in namespace."""
        items = self.endor_client.ScanProfile.list(
            max_pages=TEST_MAX_PAGES,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        got = self.endor_client.ScanProfile.get(item)
        assert got is not None
        assert got.uuid == item.uuid

    def test_scan_profile_advanced_filtering(self) -> None:
        """Test advanced filtering capabilities."""
        print("\n=== TESTING SCAN PROFILE FILTERING ===")
        # Test filtering by is_default
        default_profiles = self.endor_root_client.ScanProfile.list(
            list_params=ListParameters(
                filter="spec.is_default==true",
                page_size=TEST_PAGE_SIZE,
            ),
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(default_profiles, list), (
            "Should return a list of scan profiles"
        )
        print(f"Found {len(default_profiles)} default scan profiles")

        # Test field masking
        masked_profiles = self.endor_root_client.ScanProfile.list(
            list_params=ListParameters(
                mask="meta.name,spec.is_default",
                page_size=TEST_PAGE_SIZE,
            ),
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(masked_profiles, list), (
            "Should return a list of masked scan profiles"
        )
        if masked_profiles:
            profile = masked_profiles[0]
            assert isinstance(profile, dict), "Masked list returns wire JSON dict rows"
            meta = profile.get("meta") or {}
            assert isinstance(meta, dict)
            pname = meta.get("name", "N/A")
            print(f"Masked profile: {pname}")

    def test_scan_profile_error_handling(self) -> None:
        """Test error handling for invalid UUID."""
        # Test with invalid UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endorlabs.core.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            self.endor_root_client.ScanProfile.get("invalid-uuid")
        assert exc_info.value.resource_uuid == "invalid-uuid"
        assert exc_info.value.operation == "get"
        assert exc_info.value.status_code == 400

    @pytest.mark.writes
    def test_client_ux_create_scan_profile(self) -> None:
        """Consumer UX: client.ScanProfile.create(payload); teardown deletes."""
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
        created = None
        try:
            created = client.ScanProfile.create(payload)
        except Exception as e:
            pytest.skip(f"Scan profile create not allowed in this environment: {e}")
        try:
            assert created is not None
            assert created.meta.name == payload.meta.name
            self.created_scan_profile_uuids.append(created.uuid)
        finally:
            if created is not None:  # type: ignore[reportUnnecessaryComparison]
                try:
                    self.endor_root_client.ScanProfile.delete(created.uuid)
                except Exception as e:
                    print(f"[WARNING] Cleanup failed for {created.uuid}: {e}")

    @pytest.mark.writes
    def test_client_ux_create_scan_profile_via_kwargs(self) -> None:
        """Decoupled create: client.ScanProfile.create(name=..., namespace=...)."""
        import time

        import endorlabs

        client = endorlabs.Client(
            tenant=self.parent_namespace,
            api_client=self.client,
        )
        name = f"kwargs-profile-{int(time.time())}"
        created = None
        try:
            created = client.ScanProfile.create(
                name=name,
                description="Created via kwargs",
                is_default=False,
                namespace=self.parent_namespace,
            )
        except Exception as e:
            pytest.skip(f"Scan profile create not allowed in this environment: {e}")
        try:
            assert created is not None
            assert created.meta.name == name
            self.created_scan_profile_uuids.append(created.uuid)
        finally:
            if created is not None:  # type: ignore[reportUnnecessaryComparison]
                try:
                    self.endor_root_client.ScanProfile.delete(created.uuid)
                except Exception as e:
                    print(f"[WARNING] Cleanup failed for {created.uuid}: {e}")

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
        created = None
        try:
            created = client.ScanProfile.create(payload)
        except Exception as e:
            pytest.skip(f"Scan profile create not allowed in this environment: {e}")
        try:
            if not created:
                pytest.skip("Failed to create scan profile for update test")
            self.created_scan_profile_uuids.append(created.uuid)
            current = client.ScanProfile.get(
                created.uuid, namespace=self.parent_namespace
            )
            if not current:
                pytest.skip(f"Could not retrieve scan profile {created.uuid}")
            original_description = getattr(current.meta, "description", None) or ""
            update_payload = UpdateScanProfilePayload(
                meta=ScanProfileMetaUpdate(description="Updated by client-ux")
            )
            try:
                updated = client.ScanProfile.update(
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
                client.ScanProfile.update(
                    created.uuid,
                    restore_payload,
                    update_mask="meta.description",
                    namespace=self.parent_namespace,
                )
            except Exception as e:
                print(f"[WARNING] Failed to restore original scan profile values: {e}")
        finally:
            if created is not None:  # type: ignore[reportUnnecessaryComparison]
                try:
                    self.endor_root_client.ScanProfile.delete(created.uuid)
                except Exception as e:
                    print(f"[WARNING] Cleanup failed for {created.uuid}: {e}")

    @pytest.mark.writes
    def test_client_ux_delete_scan_profile(self) -> None:
        """Consumer UX: create then client.ScanProfile.delete(uuid)."""
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
            created = client.ScanProfile.create(payload)
        except Exception as e:
            pytest.skip(f"Scan profile create not allowed in this environment: {e}")
        if not created:
            pytest.skip("Failed to create scan profile for delete test")
        result = client.ScanProfile.delete(created.uuid)
        assert result is True
        # Do not append to created_scan_profile_uuids; resource already deleted
