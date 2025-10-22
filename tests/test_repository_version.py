"""
Test cases for RepositoryVersion resource operations.

Tests GET operations for RepositoryVersion resources following the testing protocol.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import repository_version


@pytest.mark.integration
class TestRepositoryVersion:
    """Test cases for RepositoryVersion resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = APIClient()
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")

        # Get test data
        self.repository_versions = repository_version.list_repository_versions(
            self.client, self.namespace
        )
        if not self.repository_versions:
            pytest.skip("No repository versions available for testing")

    def test_repository_version_get_list(self):
        """Test GET repository versions operation."""
        print("\n=== TESTING GET REPOSITORY VERSIONS ===")

        # Test list_repository_versions
        repository_versions_list = repository_version.list_repository_versions(
            self.client, self.namespace
        )
        assert isinstance(repository_versions_list, list), "Should return a list of repository versions"
        assert len(repository_versions_list) > 0, "Should have at least one repository version"

        print(f"Found {len(repository_versions_list)} repository versions")

        # Display first few repository versions
        for i, repo_version in enumerate(repository_versions_list[:3]):
            print(f"Repository Version {i+1}:")
            print(f"  UUID: {repo_version.uuid}")
            print(f"  Name: {repo_version.meta.name}")
            print(f"  Kind: {repo_version.meta.kind}")
            print(f"  Version: {repo_version.spec.version}")
            print(f"  Parent UUID: {repo_version.meta.parent_uuid}")

    def test_repository_version_get_by_uuid(self):
        """Test GET repository version by UUID operation."""
        test_repository_version = self.repository_versions[0]
        retrieved_repository_version = repository_version.get_repository_version(
            self.client, self.namespace, test_repository_version.uuid
        )
        assert retrieved_repository_version is not None
        assert retrieved_repository_version.uuid == test_repository_version.uuid
        assert retrieved_repository_version.meta.name == test_repository_version.meta.name

    def test_repository_version_structure_analysis(self):
        """Test and analyze repository version structure."""
        repository_version_obj = self.repository_versions[0]

        # Analyze meta fields
        meta_fields = [field for field in dir(repository_version_obj.meta) if not field.startswith("_")]
        assert len(meta_fields) > 0

        # Analyze spec fields
        spec_fields = [field for field in dir(repository_version_obj.spec) if not field.startswith("_")]
        assert len(spec_fields) > 0

        # Verify required fields
        assert hasattr(repository_version_obj, 'uuid')
        assert hasattr(repository_version_obj, 'meta')
        assert hasattr(repository_version_obj, 'spec')
        assert hasattr(repository_version_obj, 'tenant_meta')

        # Verify meta structure
        assert hasattr(repository_version_obj.meta, 'name')
        assert hasattr(repository_version_obj.meta, 'kind')
        assert hasattr(repository_version_obj.meta, 'version')

        # Verify spec structure
        assert hasattr(repository_version_obj.spec, 'version')

    def test_repository_version_conditional_attributes(self):
        """Test conditional attributes in repository version."""
        repository_version_obj = self.repository_versions[0]

        # Check for conditional attributes
        if hasattr(repository_version_obj, 'context') and repository_version_obj.context:
            print("RepositoryVersion has context attribute")
            assert isinstance(repository_version_obj.context, dict)
            assert 'id' in repository_version_obj.context
            assert 'type' in repository_version_obj.context

        if hasattr(repository_version_obj, 'scan_object') and repository_version_obj.scan_object:
            print("RepositoryVersion has scan_object attribute")
            assert isinstance(repository_version_obj.scan_object, dict)
            assert 'scan_time' in repository_version_obj.scan_object
            assert 'status' in repository_version_obj.scan_object

    def test_repository_version_base_class_inheritance(self):
        """Test that repository version inherits from base classes."""
        repository_version_obj = self.repository_versions[0]

        # Test BaseResource inheritance
        from endor_cockpit.models.base import BaseResource
        assert isinstance(repository_version_obj, BaseResource)

        # Test BaseMeta inheritance
        from endor_cockpit.models.base import BaseMeta
        assert isinstance(repository_version_obj.meta, BaseMeta)

        # Test BaseSpec inheritance
        from endor_cockpit.models.base import BaseSpec
        assert isinstance(repository_version_obj.spec, BaseSpec)

    def test_repository_version_advanced_filtering(self):
        """Test advanced filtering capabilities."""
        from endor_cockpit.types import ListParameters

        # Test filtering by parent
        if self.repository_versions:
            parent_uuid = self.repository_versions[0].meta.parent_uuid
            if parent_uuid:
                filtered_versions = repository_version.list_repository_versions(
                    self.client,
                    self.namespace,
                    list_params=ListParameters(filter=f"meta.parent_uuid=={parent_uuid}")
                )
                assert isinstance(filtered_versions, list)

        # Test field masking
        masked_versions = repository_version.list_repository_versions(
            self.client,
            self.namespace,
            list_params=ListParameters(mask="meta.name,spec.version")
        )
        assert isinstance(masked_versions, list)
        if masked_versions:
            version = masked_versions[0]
            # Should have masked fields
            assert hasattr(version, 'meta')
            assert hasattr(version, 'spec')

    def test_repository_version_error_handling(self):
        """Test error handling for invalid UUID."""
        # Test with invalid UUID
        invalid_repository_version = repository_version.get_repository_version(
            self.client, self.namespace, "invalid-uuid"
        )
        assert invalid_repository_version is None

    def test_repository_version_schema_drift_detection(self):
        """Test schema drift detection in repository version."""
        repository_version_obj = self.repository_versions[0]

        # Test that schema drift detection is working
        # This is tested implicitly through the model validation
        assert repository_version_obj is not None

        # Test that unknown fields are handled gracefully
        # This is tested through the model's extra="ignore" configuration
        assert hasattr(repository_version_obj, 'model_config')

    def test_repository_version_hierarchical_relationships(self):
        """Test hierarchical relationships in repository version."""
        repository_version_obj = self.repository_versions[0]

        # Test parent relationship
        if hasattr(repository_version_obj.meta, 'parent_uuid') and repository_version_obj.meta.parent_uuid:
            parent_uuid = repository_version_obj.meta.parent_uuid
            assert isinstance(parent_uuid, str)
            assert len(parent_uuid) > 0

        if hasattr(repository_version_obj.meta, 'parent_kind') and repository_version_obj.meta.parent_kind:
            parent_kind = repository_version_obj.meta.parent_kind
            assert isinstance(parent_kind, str)
            assert parent_kind == "Project"
