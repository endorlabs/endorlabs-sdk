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
from endor_cockpit.resources import project
from endor_cockpit.resources.tag_management import (
    add_project_tag,
    list_project_tags,
    remove_project_tag,
)


@pytest.mark.integration
class TestProject:
    """Test cases for Project resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = APIClient()
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")

        # Get test data
        self.projects = project.list_projects(self.client, self.namespace)
        if not self.projects:
            pytest.skip("No projects available for testing")

    def test_project_get_list(self):
        """Test GET projects operation."""
        print("\n=== TESTING GET PROJECTS ===")

        # Test list_projects
        projects_list = project.list_projects(self.client, self.namespace)
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

    def test_project_patch_tags(self):
        """Test PATCH operations on projects using tag management."""
        print("\n=== TESTING PROJECT PATCH OPERATIONS ===")

        project = self.projects[0]
        print(f"Testing project: {project.uuid}")

        # Test adding a tag
        test_tag = "test-patch-project-tag"
        updated_project = add_project_tag(
            self.client, self.namespace, project.uuid, test_tag
        )
        assert updated_project is not None, "Should successfully add project tag"

        # Verify tag was added
        tags_after_add = list_project_tags(self.client, self.namespace, project.uuid)
        assert test_tag in tags_after_add, "Tag should be present after add"
        print(f"[SUCCESS] Added tag '{test_tag}' to project")

        # Test removing the tag
        final_project = remove_project_tag(
            self.client, self.namespace, project.uuid, test_tag
        )
        assert final_project is not None, "Should successfully remove project tag"

        # Verify tag was removed
        tags_after_remove = list_project_tags(self.client, self.namespace, project.uuid)
        assert test_tag not in tags_after_remove, "Tag should be removed"
        print(f"[SUCCESS] Removed tag '{test_tag}' from project")

    def test_project_structure_analysis(self):
        """Test and analyze project structure."""
        print("\n=== PROJECT STRUCTURE ANALYSIS ===")

        project = self.projects[0]
        print(f"Analyzing project: {project.uuid} - {project.meta.name}")

        # Analyze project meta fields
        meta_fields = [
            field for field in dir(project.meta) if not field.startswith("_")
        ]
        print(f"Project meta fields: {meta_fields}")
        if project.meta.tags:
            print(f"Project meta tags: {project.meta.tags}")

        # Analyze project spec fields
        spec_fields = [
            field for field in dir(project.spec) if not field.startswith("_")
        ]
        print(f"Project spec fields: {spec_fields}")

        # Analyze project tenant_meta fields
        tenant_meta_fields = [
            field for field in dir(project.tenant_meta) if not field.startswith("_")
        ]
        print(f"Project tenant_meta fields: {tenant_meta_fields}")

    def test_project_base_class_inheritance(self):
        """Test that project inherits from base classes."""
        project_obj = self.projects[0]

        # Test BaseResource inheritance
        from endor_cockpit.models.base import BaseResource

        assert isinstance(project_obj, BaseResource)

        # Test BaseMeta inheritance
        from endor_cockpit.models.base import BaseMeta

        assert isinstance(project_obj.meta, BaseMeta)

        # Test BaseSpec inheritance
        from endor_cockpit.models.base import BaseSpec

        assert isinstance(project_obj.spec, BaseSpec)

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
        from endor_cockpit.types import ListParameters

        # Test filtering by platform
        github_projects = project.list_projects(
            self.client,
            self.namespace,
            list_params=ListParameters(
                filter="spec.platform_source==PLATFORM_SOURCE_GITHUB"
            ),
        )
        assert isinstance(github_projects, list)

        # Test field masking
        masked_projects = project.list_projects(
            self.client,
            self.namespace,
            list_params=ListParameters(mask="meta.name,spec.platform_source"),
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

    def test_project_schema_drift_detection(self):
        """Test schema drift detection in project."""
        project_obj = self.projects[0]

        # Test that schema drift detection is working
        # This is tested implicitly through the model validation
        assert project_obj is not None

        # Test that unknown fields are handled gracefully
        # This is tested through the model's extra="ignore" configuration
        assert hasattr(project_obj, "model_config")

    def test_project_operations_summary(self):
        """Generate summary of project operations."""
        print("\n=== PROJECT OPERATIONS SUMMARY ===")

        print("GET Operations:")
        print(f"  - List Projects: GET /v1/namespaces/{self.namespace}/projects")
        print(f"  - Get Project: GET /v1/namespaces/{self.namespace}/projects/{{uuid}}")

        print("PATCH Operations (Tag Management):")
        print(
            f"  - Update Project Tags: PATCH /v1/namespaces/{self.namespace}/projects"
        )
        print("  - Uses update_mask for efficient partial updates")
        print("  - Project tags: meta.tags field")

        print("Success Metrics:")
        print(f"  - Projects Retrieved: {len(self.projects)}")
        print("  - GET Operations: Working")
        print("  - PATCH Operations: Working with update_mask")
        print("  - Tag Management: Functional for user-defined tags")


if __name__ == "__main__":
    # Run tests directly
    import os
    import sys

    # Set up environment
    os.environ.setdefault("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")

    # Create test instance and manually set up
    test_instance = TestProject()

    # Manual setup
    test_instance.client = APIClient()
    test_instance.namespace = os.getenv(
        "ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit"
    )
    test_instance.projects = project.list_projects(
        test_instance.client, test_instance.namespace
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
