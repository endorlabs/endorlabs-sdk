"""Test cases for Project resource operations.

Tests GET and PATCH operations for Project resources, including tag management.
Follows the testing protocol for comprehensive coverage.

Greenfield alias unit tests live in tests/unit/models/test_greenfield_aliases.py.
"""

import pytest

import endorlabs
from endorlabs.resources.project import (
    ProjectMetaUpdate,
    UpdateProjectPayload,
    associate_scan_profile_with_project,
    verify_scan_profile_association,
)
from endorlabs.resources.scan_profile import (
    AutomatedScanParameters,
    CreateScanProfilePayload,
    ScanProfileMetaCreate,
    ScanProfileSpecCreate,
)
from tests.conftest import TEST_MAX_PAGES, TEST_MAX_PAGES_TRAVERSE, TEST_PAGE_SIZE


@pytest.mark.integration
class TestProject:
    """Test cases for Project resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace, root_namespace) -> None:
        """Set up test environment (client and namespace from conftest)."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.endor_root_client = endorlabs.Client(
            tenant=root_namespace, api_client=api_client
        )
        self.created_scan_profile_uuids = []

        # Get test data with pagination limits
        from endorlabs.exceptions import NotFoundError, ServerError
        from endorlabs.types import ListParameters

        try:
            self.projects = self.endor_client.project.list(
                list_params=ListParameters(page_size=TEST_PAGE_SIZE),
                max_pages=TEST_MAX_PAGES,
            )
        except NotFoundError:
            pytest.skip(
                "List returned 404 (resource does not exist to user: "
                "namespace not accessible to credential or resource no longer exists)"
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not self.projects:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

    def teardown_method(self) -> None:
        """Clean up any resources created during tests."""
        if hasattr(self, "created_scan_profile_uuids"):
            for scan_profile_uuid in self.created_scan_profile_uuids:
                try:
                    self.endor_client.scan_profile.delete(scan_profile_uuid)
                    print(f"[CLEANUP] Deleted test scan profile: {scan_profile_uuid}")
                except Exception as e:
                    print(
                        f"[WARNING] Failed to delete test scan profile "
                        f"{scan_profile_uuid}: {e}"
                    )
            self.created_scan_profile_uuids.clear()

    def test_project_list(self) -> None:
        """LIST from tenant root with traverse (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        result = client.project.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_project_get(self) -> None:
        """GET first item from LIST (root + traverse) (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.project.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        got = client.project.get(item)
        assert got is not None
        assert got.uuid == item.uuid

    def test_project_spec_has_scan_profile_and_archived_attrs(self) -> None:
        """Project spec has scan_profile_uuid, toolchain_profile_uuid and related."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.project.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        assert item.spec is not None
        assert hasattr(item.spec, "scan_profile_uuid")
        assert hasattr(item.spec, "toolchain_profile_uuid")
        assert hasattr(item.spec, "ingestion_token")
        assert hasattr(item.spec, "is_archived")
        got = client.project.get(item)
        if got and got.spec:
            assert hasattr(got.spec, "scan_profile_uuid")
            assert hasattr(got.spec, "toolchain_profile_uuid")
            assert hasattr(got.spec, "ingestion_token")
            assert hasattr(got.spec, "is_archived")

    @pytest.mark.writes
    def test_associate_scan_profile_with_project(self) -> None:
        """Test associating a scan profile with a project.

        Local-only: creates scan profile and mutates project (403 in CI).
        """
        print("\n=== TESTING ASSOCIATE SCAN PROFILE WITH PROJECT ===")

        if not self.projects:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

        test_project = self.projects[0]
        project_uuid = test_project.uuid

        # Create a test scan profile
        print("Creating test scan profile...")
        automated_params = AutomatedScanParameters(excluded_paths=["test/**"])
        payload = CreateScanProfilePayload(
            meta=ScanProfileMetaCreate(
                name=f"test-profile-{project_uuid[:8]}",
                description="Test scan profile for association",
            ),
            spec=ScanProfileSpecCreate(
                automated_scan_parameters=automated_params,
                is_default=False,
            ),
            propagate=False,
        )

        created_profile = self.endor_client.scan_profile.create(payload)
        if not created_profile:
            pytest.skip("Failed to create test scan profile")

        scan_profile_uuid = created_profile.uuid
        print(f"Created scan profile: {scan_profile_uuid}")

        # Track for cleanup
        self.created_scan_profile_uuids.append(scan_profile_uuid)

        try:
            # Associate scan profile with project
            print(
                f"Associating scan profile {scan_profile_uuid} with project "
                f"{project_uuid}..."
            )
            updated_project = associate_scan_profile_with_project(
                self.client, self.namespace, project_uuid, scan_profile_uuid
            )

            assert updated_project is not None, (
                "Should successfully associate scan profile"
            )
            assert updated_project.spec.scan_profile_uuid == scan_profile_uuid, (
                "Project should have the associated scan profile UUID"
            )

            print("✅ Successfully associated scan profile with project")

            # Verify association
            print("Verifying scan profile association...")
            is_associated = verify_scan_profile_association(
                self.client, self.namespace, project_uuid, scan_profile_uuid
            )
            assert is_associated, "Verification should confirm association"

            print("✅ Verification successful")

        finally:
            # Clean up: Remove scan profile association
            print("Cleaning up: Removing scan profile association...")
            current_project = self.endor_client.project.get(project_uuid)
            if current_project:
                spec_dict = current_project.spec.model_dump()
                spec_dict["scan_profile_uuid"] = None
                request_data = {
                    "object": {
                        "uuid": project_uuid,
                        "tenant_meta": current_project.tenant_meta.model_dump(),
                        "meta": {"name": current_project.meta.name},
                        "spec": spec_dict,
                    },
                    "request": {"update_mask": "spec.scan_profile_uuid"},
                }
                try:
                    self.client.patch(
                        f"v1/namespaces/{self.namespace}/projects",
                        json=request_data,
                        headers={"Accept": "application/json"},
                    )
                    print("✅ Cleaned up scan profile association")
                except Exception as e:
                    print(f"⚠️ Warning: Could not clean up association: {e}")
            # Delete the test scan profile
            try:
                self.endor_client.scan_profile.delete(scan_profile_uuid)
                print("✅ Deleted test scan profile")
            except Exception as e:
                print(
                    f"[WARNING] Cleanup failed for scan profile "
                    f"{scan_profile_uuid}: {e}"
                )

    def test_project_advanced_filtering(self) -> None:
        """Test advanced filtering capabilities."""
        # Test filtering by platform
        from endorlabs.types import ListParameters

        github_projects = self.endor_client.project.list(
            list_params=ListParameters(
                filter="spec.platform_source==PLATFORM_SOURCE_GITHUB",
                page_size=TEST_PAGE_SIZE,
            ),
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(github_projects, list)

        # Test field masking
        masked_projects = self.endor_client.project.list(
            list_params=ListParameters(
                mask="meta.name,spec.platform_source",
                page_size=TEST_PAGE_SIZE,
            ),
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(masked_projects, list)
        if masked_projects:
            proj = masked_projects[0]
            # Should have masked fields
            assert hasattr(proj, "meta")
            assert hasattr(proj, "spec")

    @pytest.mark.writes
    def test_project_update_with_mask(self) -> None:
        """Test UPDATE project operation with update_mask parameter.

        Local-only: updating projects requires elevated permissions (403 in CI).
        """
        print("\n=== TESTING PROJECT UPDATE WITH MASK ===")

        if not self.projects:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

        test_project = self.projects[0]
        project_uuid = test_project.uuid

        # Get current project state
        current_project = self.endor_client.project.get(project_uuid)
        if not current_project:
            pytest.skip(f"Could not retrieve project {project_uuid}")

        # Store original values
        original_description = current_project.meta.description
        original_tags = current_project.meta.tags or []

        # Create update payload - only update safe fields
        new_description = (
            f"{original_description} [Updated by test]"
            if original_description
            else "Updated description for test"
        )
        new_tags = [*original_tags, "test-update", "mask-test"]

        update_payload = UpdateProjectPayload(
            meta=ProjectMetaUpdate(
                description=new_description,
                tags=new_tags,
            )
        )

        print(f"Updating project: {project_uuid}")
        print(f"New description: {new_description}")
        print(f"New tags: {new_tags}")

        # Update the project with update_mask
        updated_project = self.endor_client.project.update(
            project_uuid,
            update_payload,
            update_mask="meta.description,meta.tags",
        )

        assert updated_project is not None, "Project update should succeed"
        assert updated_project.meta.description == new_description, (
            "Project description should be updated"
        )
        assert "test-update" in updated_project.meta.tags, (
            "Updated tag should be present"
        )
        assert "mask-test" in updated_project.meta.tags, "Updated tag should be present"

        print(f"[SUCCESS] Project updated: {updated_project.uuid}")
        print(f"Updated description: {updated_project.meta.description}")
        print(f"Updated tags: {updated_project.meta.tags}")

        # Restore original values if possible
        restore_payload = UpdateProjectPayload(
            meta=ProjectMetaUpdate(
                description=original_description,
                tags=original_tags,
            )
        )
        try:
            self.endor_client.project.update(
                project_uuid,
                restore_payload,
                update_mask="meta.description,meta.tags",
            )
            print("[CLEANUP] Restored original project values")
        except Exception as e:
            print(f"[WARNING] Failed to restore original values: {e}")

    def test_project_error_handling(self) -> None:
        """Test error handling for invalid UUID."""
        # Test with invalid UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endorlabs.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            self.endor_client.project.get("invalid-uuid")
        assert exc_info.value.resource_uuid == "invalid-uuid"
        assert exc_info.value.operation == "get"
        assert exc_info.value.status_code == 400

    @pytest.mark.writes
    def test_client_ux_update_project(self) -> None:
        """Consumer UX: client.project.get() then update then revert."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.namespace,
            api_client=self.client,
        )
        projects = client.project.list(max_pages=TEST_MAX_PAGES)
        if not projects:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = projects[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.namespace
        )
        current = client.project.get(item.uuid, namespace=ns)
        if not current:
            pytest.skip(f"Could not retrieve project {item.uuid}")
        original_description = current.meta.description
        original_tags = current.meta.tags or []
        new_description = (
            f"{original_description} [client-ux]"
            if original_description
            else "client-ux"
        )
        new_tags = [*original_tags, "client-ux-update"]
        try:
            updated = client.project.update(
                current,
                meta_description=new_description,
                meta_tags=new_tags,
            )
        except Exception as e:
            pytest.skip(f"Project update not allowed in this environment: {e}")
        assert updated is not None
        assert updated.meta.description == new_description
        try:
            client.project.update(
                updated,
                meta_description=original_description,
                meta_tags=original_tags,
            )
        except Exception as e:
            print(f"[WARNING] Failed to restore original project values: {e}")
