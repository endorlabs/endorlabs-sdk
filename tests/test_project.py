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


@pytest.mark.integration
class TestProject:
    """Test cases for Project resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Set up test environment."""
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Track created resources for cleanup
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
            pytest.skip("List returned 404 (filter/auth or scope)")
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

    def test_project_get_list(self) -> None:
        """Test GET projects operation."""
        print("\n=== TESTING GET PROJECTS ===")

        import conftest

        from endorlabs.exceptions import ServerError
        from endorlabs.types import ListParameters

        try:
            projects_list = project.list_projects(
                self.client,
                self.namespace,
                list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
                max_pages=conftest.TEST_MAX_PAGES,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        assert isinstance(projects_list, list), "Should return a list of projects"
        assert all(
            isinstance(x, Project) for x in projects_list
        ), "All list items should be Project instances"
        if len(projects_list) == 0:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

        print(f"Found {len(projects_list)} projects")

        # Display project details
        for proj in projects_list:
            name = proj.meta.name if proj.meta else None
            print(f"Project {proj.uuid}: {name}")
            if proj.meta.tags:
                print(f"  Project tags: {proj.meta.tags}")

    def test_project_get_by_uuid(self) -> None:
        """Test GET project by UUID operation."""
        print("\n=== TESTING GET PROJECT BY UUID ===")

        test_project = self.projects[0]
        retrieved_project = project.get_project(
            self.client, self.namespace, test_project.uuid
        )

        assert retrieved_project is not None, (
            "Should successfully retrieve project by UUID"
        )
        assert retrieved_project.uuid == test_project.uuid, (
            "Retrieved project should match original"
        )
        assert retrieved_project.meta.name == test_project.meta.name, (
            "Project name should match"
        )

        print(f"Successfully retrieved project: {retrieved_project.uuid}")
        print(f"Project name: {retrieved_project.meta.name}")
        if retrieved_project.meta.tags:
            print(f"Project tags: {retrieved_project.meta.tags}")

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

    def test_client_recommended_ux_list_projects(self) -> None:
        """Recommended UX: endorlabs.Client(tenant=...); client.projects.list()."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.namespace,
            max_retries=2,
            backoff_factor=0.1,
            auth_method="api-key",
        )
        projects = client.projects.list(max_pages=1)
        assert isinstance(projects, list)


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

        # Run all tests
        test_instance.test_project_get_list()
        test_instance.test_project_get_by_uuid()
        test_instance.test_project_patch_tags()
        test_instance.test_project_structure_analysis()
        test_instance.test_project_operations_summary()

        print("\n[SUCCESS] All project tests completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
