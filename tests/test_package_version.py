"""
Integration tests for Package Version resource operations.

These tests verify the complete CRUD lifecycle for Package Version resources,
including tag management operations and error handling scenarios.
"""

import os

import pytest

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import package_version


@pytest.mark.integration
class TestPackageVersion:
    """Test cases for Package Version operations."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = APIClient()
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")
        self.package_versions = package_version.list_package_versions(self.client, self.namespace)
        if not self.package_versions:
            pytest.skip("No package versions available for testing")

    def test_package_version_get_list(self):
        """Test GET package-versions operation."""
        package_versions_list = package_version.list_package_versions(self.client, self.namespace)
        assert isinstance(package_versions_list, list)
        assert len(package_versions_list) > 0

        # Verify structure
        for pv in package_versions_list:
            assert hasattr(pv, 'uuid')
            assert hasattr(pv, 'meta')
            assert hasattr(pv, 'spec')
            assert hasattr(pv, 'tenant_meta')

            # Verify meta fields
            assert hasattr(pv.meta, 'name')
            assert hasattr(pv.meta, 'description')
            assert hasattr(pv.meta, 'create_time')
            assert hasattr(pv.meta, 'created_by')
            assert hasattr(pv.meta, 'update_time')
            assert hasattr(pv.meta, 'updated_by')
            assert hasattr(pv.meta, 'tags')

            # Verify spec fields
            assert hasattr(pv.spec, 'package_name')
            assert hasattr(pv.spec, 'version')
            assert hasattr(pv.spec, 'ecosystem')
            assert hasattr(pv.spec, 'repository_version_uuid')

    def test_package_version_get_by_uuid(self):
        """Test GET package-version by UUID operation."""
        test_package_version = self.package_versions[0]
        retrieved_package_version = package_version.get_package_version(
            self.client, self.namespace, test_package_version.uuid
        )
        assert retrieved_package_version is not None
        assert retrieved_package_version.uuid == test_package_version.uuid
        assert retrieved_package_version.meta.name == test_package_version.meta.name
        assert retrieved_package_version.spec.package_name == test_package_version.spec.package_name
        assert retrieved_package_version.spec.version == test_package_version.spec.version

    def test_package_version_patch_tags(self):
        """Test PATCH operations using tag management."""
        test_package_version = self.package_versions[0]
        test_tag = "test-tag"

        # Add tag
        updated_package_version = add_package_version_tag(
            self.client, self.namespace, test_package_version.uuid, test_tag
        )
        assert updated_package_version is not None
        assert test_tag in updated_package_version.meta.tags

        # List tags
        tags = list_package_version_tags(self.client, self.namespace, test_package_version.uuid)
        assert test_tag in tags

        # Remove tag
        final_package_version = remove_package_version_tag(
            self.client, self.namespace, test_package_version.uuid, test_tag
        )
        assert final_package_version is not None
        assert test_tag not in final_package_version.meta.tags

    def test_package_version_structure_analysis(self):
        """Test and analyze package version structure."""
        package_version_obj = self.package_versions[0]

        # Analyze meta fields
        meta_fields = [field for field in dir(package_version_obj.meta) if not field.startswith("_")]
        assert len(meta_fields) > 0

        # Analyze spec fields
        spec_fields = [field for field in dir(package_version_obj.spec) if not field.startswith("_")]
        assert len(spec_fields) > 0

        # Verify required fields are present
        assert package_version_obj.meta.name is not None
        assert package_version_obj.spec.package_name is not None
        assert package_version_obj.spec.version is not None
        assert package_version_obj.spec.ecosystem is not None

    def test_package_version_operations_summary(self):
        """Test and summarize package version operations."""
        package_versions_list = package_version.list_package_versions(self.client, self.namespace)

        print("\n=== Package Version Operations Summary ===")
        print(f"Total package versions: {len(package_versions_list)}")

        # Analyze package versions by ecosystem
        ecosystem_counts = {}
        for pv in package_versions_list:
            ecosystem = str(pv.spec.ecosystem) if pv.spec.ecosystem else 'Unknown'
            ecosystem_counts[ecosystem] = ecosystem_counts.get(ecosystem, 0) + 1

        print("Ecosystem distribution:")
        for ecosystem, count in ecosystem_counts.items():
            print(f"  {ecosystem}: {count}")

        # Analyze package versions by tags
        tagged_count = sum(1 for pv in package_versions_list if pv.meta.tags)
        print(f"Package versions with tags: {tagged_count}")

        # Show sample package versions
        print("\nSample package versions:")
        for i, pv in enumerate(package_versions_list[:3]):
            print(f"  {i+1}. {pv.meta.name} ({pv.spec.ecosystem})")
            if pv.meta.tags:
                print(f"     Tags: {', '.join(pv.meta.tags)}")

        assert len(package_versions_list) > 0


def add_package_version_tag(client: APIClient, namespace: str, package_version_uuid: str, tag: str):
    """Add a tag to a package version."""
    from endor_cockpit.resources.package_version import (
        PackageVersionMetaUpdate,
        UpdatePackageVersionPayload,
    )

    # Get current package version
    current_pv = package_version.get_package_version(client, namespace, package_version_uuid)
    if not current_pv:
        return None

    # Add tag to existing tags
    current_tags = current_pv.meta.tags or []
    if tag not in current_tags:
        current_tags.append(tag)

    # Update with new tags
    payload = UpdatePackageVersionPayload(
        meta=PackageVersionMetaUpdate(tags=current_tags)
    )
    return package_version.update_package_version(
        client, namespace, package_version_uuid, payload, "meta.tags"
    )


def remove_package_version_tag(client: APIClient, namespace: str, package_version_uuid: str, tag: str):
    """Remove a tag from a package version."""
    from endor_cockpit.resources.package_version import (
        PackageVersionMetaUpdate,
        UpdatePackageVersionPayload,
    )

    # Get current package version
    current_pv = package_version.get_package_version(client, namespace, package_version_uuid)
    if not current_pv:
        return None

    # Remove tag from existing tags
    current_tags = current_pv.meta.tags or []
    if tag in current_tags:
        current_tags.remove(tag)

    # Update with modified tags
    payload = UpdatePackageVersionPayload(
        meta=PackageVersionMetaUpdate(tags=current_tags)
    )
    return package_version.update_package_version(
        client, namespace, package_version_uuid, payload, "meta.tags"
    )


def list_package_version_tags(client: APIClient, namespace: str, package_version_uuid: str):
    """List tags for a package version."""
    pv = package_version.get_package_version(client, namespace, package_version_uuid)
    return pv.meta.tags if pv and pv.meta.tags else []
