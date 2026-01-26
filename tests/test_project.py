"""
Test cases for Project resource operations.

Tests GET and PATCH operations for Project resources, including tag management.
Follows the testing protocol for comprehensive coverage.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import project, scan_profile
from endor_cockpit.resources.project import (
    associate_scan_profile_with_project,
    verify_scan_profile_association,
)
from endor_cockpit.resources.scan_profile import (
    AutomatedScanParameters,
    CreateScanProfilePayload,
    ScanProfileMetaCreate,
    ScanProfileSpecCreate,
)


@pytest.mark.integration
class TestProject:
    """Test cases for Project resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.tgowan-endor")

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Get test data with pagination limits
        import conftest

        from endor_cockpit.types import ListParameters

        self.projects = project.list_projects(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        if not self.projects:
            pytest.skip("No projects available for testing")

    def test_project_get_list(self):
        """Test GET projects operation."""
        print("\n=== TESTING GET PROJECTS ===")

        # Test list_projects with pagination limits
        import conftest

        from endor_cockpit.types import ListParameters

        projects_list = project.list_projects(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(projects_list, list), "Should return a list of projects"
        assert len(projects_list) > 0, "Should have at least one project"

        print(f"Found {len(projects_list)} projects")

        # Display project details
        for proj in projects_list:
            print(f"Project {proj.uuid}: {proj.meta.name}")
            if proj.meta.tags:
                print(f"  Project tags: {proj.meta.tags}")

    def test_project_get_by_uuid(self):
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

    def test_associate_scan_profile_with_project(self):
        """Test associating a scan profile with a project."""
        print("\n=== TESTING ASSOCIATE SCAN PROFILE WITH PROJECT ===")

        if not self.projects:
            pytest.skip("No projects available for testing")

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

            # Delete test scan profile
            try:
                scan_profile.delete_scan_profile(
                    self.client, self.namespace, scan_profile_uuid
                )
                print("✅ Deleted test scan profile")
            except Exception as e:
                print(f"⚠️ Warning: Could not delete test scan profile: {e}")

    def test_project_conditional_attributes(self):
        """Test conditional attributes in project."""
        project_obj = self.projects[0]

        # Check for conditional attributes
        if hasattr(project_obj, "processing_status") and project_obj.processing_status:
            print("Project has processing_status attribute")
            # processing_status is a Pydantic model, not a dict
            assert hasattr(project_obj.processing_status, "scan_state")
            assert hasattr(project_obj.processing_status, "scan_time")
            assert hasattr(project_obj.processing_status, "disable_automated_scan")

    def test_project_advanced_filtering(self):
        """Test advanced filtering capabilities."""
        # Test filtering by platform
        import conftest

        from endor_cockpit.types import ListParameters

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

    def test_project_error_handling(self):
        """Test error handling for invalid UUID."""
        # Test with invalid UUID
        invalid_project = project.get_project(
            self.client, self.namespace, "invalid-uuid"
        )
        assert invalid_project is None


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
    import conftest

    from endor_cockpit.types import ListParameters

    test_instance.client = APIClient(auth_method="api-key")
    test_instance.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.tgowan-endor")
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
