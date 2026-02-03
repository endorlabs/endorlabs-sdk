"""Test cases for Project resource operations.

Tests GET and PATCH operations for Project resources, including tag management.
Follows the testing protocol for comprehensive coverage.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import conftest

from endorlabs.api_client import APIClient
from endorlabs.resources import project, scan_profile
from endorlabs.resources.project import (
    Project,
    ProjectMeta,
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


class TestProjectGreenfieldAlias:
    """Unit tests: greenfield attribute names (processing_status, index_data).

    These tests assert .processing_status and .meta.index_data and serialization
    so that after renaming project_processing_status -> processing_status and
    project_index_data -> index_data, they pass without change.
    """

    def test_project_processing_status_attribute_and_serialization(self) -> None:
        """Project exposes .processing_status and serializes as 'processing_status'."""
        payload = {
            "uuid": "proj-uuid",
            "meta": {"name": "proj-meta"},
            "spec": {},
            "tenant_meta": {"namespace": "test-ns"},
            "processing_status": {
                "disable_automated_scan": False,
                "scan_state": "idle",
            },
        }
        project = Project(**payload)
        assert project.processing_status is not None
        assert getattr(project.processing_status, "scan_state", None) == "idle"
        dumped = project.model_dump(by_alias=True)
        assert "processing_status" in dumped
        assert dumped["processing_status"] is not None

    def test_project_meta_index_data_attribute_and_serialization(self) -> None:
        """ProjectMeta exposes .index_data and serializes with key 'index_data'."""
        meta = ProjectMeta(
            name="proj-meta",
            index_data={"data": ["d1"], "tenant": "t1"},
        )
        assert getattr(meta, "index_data", None) is not None
        index_data = getattr(meta, "index_data", None)
        assert index_data is not None
        if hasattr(index_data, "tenant"):
            assert index_data.tenant == "t1"
        else:
            assert index_data.get("tenant") == "t1"
        dumped_meta = meta.model_dump(by_alias=True)
        assert "index_data" in dumped_meta
        assert dumped_meta["index_data"] is not None


@pytest.mark.integration
class TestProject:
    """Test cases for Project resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace, root_namespace) -> None:
        """Set up test environment (client and namespace from conftest)."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.created_scan_profile_uuids = []

        # Get test data with pagination limits
        from endorlabs.exceptions import NotFoundError, ServerError
        from endorlabs.types import ListParameters

        try:
            self.projects = project.list_projects(
                self.client,
                self.namespace,
                list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
                max_pages=conftest.TEST_MAX_PAGES,
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
                    scan_profile.delete_scan_profile(
                        self.client, self.namespace, scan_profile_uuid
                    )
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
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
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
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        got = client.project.get(item)
        assert got is not None
        assert got.uuid == item.uuid

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

        created_profile = scan_profile.create_scan_profile(
            self.client, self.namespace, payload
        )
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
            current_project = project.get_project(
                self.client, self.namespace, project_uuid
            )
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
                scan_profile.delete_scan_profile(
                    self.client, self.namespace, scan_profile_uuid
                )
                print("✅ Deleted test scan profile")
            except Exception as e:
                print(
                    f"[WARNING] Cleanup failed for scan profile "
                    f"{scan_profile_uuid}: {e}"
                )

    def test_project_advanced_filtering(self) -> None:
        """Test advanced filtering capabilities."""
        # Test filtering by platform
        import conftest

        from endorlabs.types import ListParameters

        github_projects = project.list_projects(
            self.client,
            self.namespace,
            list_params=ListParameters(
                filter="spec.platform_source==PLATFORM_SOURCE_GITHUB",
                page_size=conftest.TEST_PAGE_SIZE,
            ),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(github_projects, list)

        # Test field masking
        masked_projects = project.list_projects(
            self.client,
            self.namespace,
            list_params=ListParameters(
                mask="meta.name,spec.platform_source",
                page_size=conftest.TEST_PAGE_SIZE,
            ),
            max_pages=conftest.TEST_MAX_PAGES,
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
        current_project = project.get_project(self.client, self.namespace, project_uuid)
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
        updated_project = project.update_project(
            self.client,
            self.namespace,
            project_uuid,
            update_payload,
            "meta.description,meta.tags",
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
            project.update_project(
                self.client,
                self.namespace,
                project_uuid,
                restore_payload,
                "meta.description,meta.tags",
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
            project.get_project(self.client, self.namespace, "invalid-uuid")
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
        projects = client.project.list(max_pages=conftest.TEST_MAX_PAGES)
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


if __name__ == "__main__":
    # Run tests directly
    import os
    import sys

    # Set up environment
    # Require ENDOR_NAMESPACE to be set
    if not os.getenv("ENDOR_NAMESPACE"):
        print("ERROR: ENDOR_NAMESPACE environment variable must be set")
        sys.exit(1)

    # Create test instance and manually set up
    test_instance = TestProject()

    # Manual setup
    from endorlabs.types import ListParameters

    test_instance.client = APIClient(auth_method="api-key")
    test_instance.namespace = os.getenv(
        "ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT
    )
    test_instance.projects = project.list_projects(
        test_instance.client,
        test_instance.namespace,
        list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
        max_pages=conftest.TEST_MAX_PAGES,
    )

    try:
        print("Running project resource tests...")
        exit_code = pytest.main([__file__, "-v", "-s"])
        if exit_code != 0:
            sys.exit(exit_code)
        print("\n[SUCCESS] All project tests completed successfully!")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        test_instance.client.close()
