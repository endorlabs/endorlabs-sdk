"""Test cases for PackageLicense resource operations.

Tests GET and LIST operations for PackageLicense resources.
PackageLicense represents license information for package versions in the OSS namespace.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import package_license
from endor_cockpit.types import ListParameters


@pytest.mark.integration
class TestPackageLicense:
    """Test cases for PackageLicense resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self) -> None:
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        import conftest

        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Extract parent namespace from child namespace if needed
        parts = self.namespace.split(".")
        self.parent_namespace = parts[0] if len(parts) > 1 else self.namespace

    @pytest.fixture
    def sample_package_license(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Only fetches 1 item without traverse for fast setup. Tests that need
        sample data should request this fixture explicitly.
        """
        # Fetch 1 item without traverse (fast)
        results = package_license.list_package_licenses(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=1),
            max_pages=1,
        )
        if not results:
            pytest.skip("No package licenses available for testing")
        return results[0]  # Return single item, not list

    def test_package_license_get_list(self) -> None:
        """Test GET package-licenses operation."""
        print("\n=== TESTING GET PACKAGE LICENSE ===")

        # Test list_package_licenses with pagination limits
        import conftest

        package_license_list = package_license.list_package_licenses(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(package_license_list, list), (
            "Should return a list of package licenses"
        )
        assert len(package_license_list) > 0, "Should have at least one package license"

        print(f"Found {len(package_license_list)} package license records")

        # Verify structure
        for pl in package_license_list[:5]:  # Show first 5
            assert hasattr(pl, "uuid")
            assert hasattr(pl, "meta")
            assert hasattr(pl, "spec")
            assert hasattr(pl, "tenant_meta")

            # Verify meta fields
            assert hasattr(pl.meta, "name")
            assert hasattr(pl.meta, "create_time")

            # Verify spec fields
            if pl.spec:
                assert hasattr(pl.spec, "project_uuid")
                assert hasattr(pl.spec, "all_licenses")

                if pl.meta:
                    print(f"PackageLicense {pl.uuid}: {pl.meta.name}")

    def test_package_license_get_by_uuid(self, sample_package_license) -> None:
        """Test GET package-license by UUID operation."""
        print("\n=== TESTING GET PACKAGE LICENSE BY UUID ===")

        test_pl = sample_package_license
        # Use the package license's actual namespace (should be "oss")
        pl_namespace = (
            test_pl.tenant_meta.namespace
            if test_pl.tenant_meta
            else self.parent_namespace
        )
        retrieved_pl = package_license.get_package_license(
            self.client, pl_namespace, test_pl.uuid
        )

        assert retrieved_pl is not None, (
            "Should successfully retrieve package license by UUID"
        )
        assert retrieved_pl.uuid == test_pl.uuid, (
            "Retrieved package license should match original"
        )
        if retrieved_pl.meta and test_pl.meta:
            assert retrieved_pl.meta.name == test_pl.meta.name, (
                "Package license name should match"
            )

        print(f"Successfully retrieved package license: {retrieved_pl.uuid}")
        if retrieved_pl.meta:
            print(f"Package license name: {retrieved_pl.meta.name}")

    def test_package_license_pagination(self) -> None:
        """Test pagination capabilities."""
        # Test with page size and max_pages limit
        import conftest

        paginated_results = package_license.list_package_licenses(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=5),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(paginated_results, list)
        assert len(paginated_results) > 0

    def test_package_license_error_handling(self) -> None:
        """Test error handling for invalid UUID."""
        # Test with invalid UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endor_cockpit.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            package_license.get_package_license(
                self.client, self.parent_namespace, "invalid-uuid"
            )
        assert exc_info.value.resource_uuid == "invalid-uuid"
        assert exc_info.value.operation == "get"
        assert exc_info.value.status_code == 400

    def test_package_license_filter_by_project(self, sample_package_license) -> None:
        """Test filtering package licenses by project UUID."""
        print("\n=== TESTING FILTER PACKAGE LICENSE BY PROJECT ===")

        # Get first package license to extract project UUID
        first_pl = sample_package_license
        if not first_pl.spec or not first_pl.spec.project_uuid:
            pytest.skip("Package license has no project_uuid")

        project_uuid = first_pl.spec.project_uuid

        # Filter package licenses by project with pagination limits
        import conftest

        list_params = ListParameters(
            filter=f'spec.project_uuid=="{project_uuid}"',
            page_size=conftest.TEST_PAGE_SIZE,
        )

        filtered_results = package_license.list_package_licenses(
            self.client,
            self.parent_namespace,
            list_params,
            max_pages=conftest.TEST_MAX_PAGES,
        )

        assert isinstance(filtered_results, list), (
            "Should return a list of filtered package licenses"
        )
        assert len(filtered_results) > 0, (
            "Should have at least one package license for the project"
        )

        # Verify all results belong to the project
        for result in filtered_results:
            if result.spec:
                assert result.spec.project_uuid == project_uuid, (
                    "All filtered results should belong to the project"
                )

        print(
            f"Found {len(filtered_results)} package license records "
            f"for project {project_uuid}"
        )

    def test_package_license_field_masking(self, sample_package_license) -> None:
        """Test field masking for package licenses."""
        print("\n=== TESTING PACKAGE LICENSE FIELD MASKING ===")
        import conftest

        # Test field masking
        masked_results = package_license.list_package_licenses(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(
                mask="meta.name,spec.project_uuid",
                page_size=conftest.TEST_PAGE_SIZE,
            ),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(masked_results, list), (
            "Should return a list of masked package licenses"
        )
        if masked_results:
            result = masked_results[0]
            # Should have masked fields
            assert hasattr(result, "meta")
            assert hasattr(result, "spec")
            print(f"Masked package license: {result.meta.name}")

    def test_package_license_oss_namespace_verification(self) -> None:
        """Test that all operations use OSS namespace regardless of parameter."""
        print("\n=== TESTING OSS NAMESPACE VERIFICATION ===")

        import conftest

        # Test with different namespace parameters - all should return OSS data
        test_namespaces = [
            "endor-solutions-tgowan",
            conftest.TEST_NAMESPACE_DEFAULT,
            "some-other-namespace",
            "oss",  # Even if explicitly "oss"
        ]

        for test_ns in test_namespaces:
            results = package_license.list_package_licenses(
                self.client,
                test_ns,
                list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
                max_pages=conftest.TEST_MAX_PAGES,
            )

            # All results should have tenant_meta.namespace == "oss"
            for result in results:
                assert result.tenant_meta is not None, (
                    "Package license should have tenant_meta"
                )
                assert result.tenant_meta.namespace == "oss", (
                    f"Package license should be in OSS namespace, "
                    f"got {result.tenant_meta.namespace} (tested with {test_ns})"
                )

        print("Verified all operations use OSS namespace regardless of parameter")

    def test_package_license_info_structure(self, sample_package_license) -> None:
        """Test PackageLicenseInfo structure and fields."""
        print("\n=== TESTING PACKAGE LICENSE INFO STRUCTURE ===")

        pl = sample_package_license

        # Test all_licenses structure
        self._test_license_list_structure(
            pl.spec.all_licenses if pl.spec else None, "all_licenses"
        )

        # Test package_manager_licenses structure
        self._test_license_list_structure(
            pl.spec.package_manager_licenses if pl.spec else None,
            "package_manager_licenses",
        )

        # Test code_licenses structure
        self._test_license_list_structure(
            pl.spec.code_licenses if pl.spec else None, "code_licenses"
        )

        # Test declared_code_licenses structure
        self._test_license_list_structure(
            pl.spec.declared_code_licenses if pl.spec else None,
            "declared_code_licenses",
        )

        # Test copyrights structure
        if pl.spec and pl.spec.copyrights:
            assert isinstance(pl.spec.copyrights, dict)
            for file_name, copyright_text in list(pl.spec.copyrights.items())[:2]:
                assert isinstance(file_name, str)
                assert isinstance(copyright_text, str)

        # Test license_text structure
        if pl.spec and pl.spec.license_text:
            assert isinstance(pl.spec.license_text, dict)
            for hash_key, license_text in list(pl.spec.license_text.items())[:2]:
                assert isinstance(hash_key, str)
                assert isinstance(license_text, str)

        print("Verified PackageLicenseInfo structure and fields")

    def _test_license_list_structure(self, license_list, field_name) -> None:
        """Helper to test license list structure."""
        if license_list:
            assert isinstance(license_list, list), f"{field_name} should be a list"
            for license_info in license_list[:3]:
                assert hasattr(license_info, "license_description")
                assert license_info.license_description is not None
                assert hasattr(license_info, "spdx_id")
                assert hasattr(license_info, "spdx_expr")
                assert hasattr(license_info, "type")
                if license_info.spdx_id:
                    print(f"License: {license_info.license_description}")
                    print(f"  SPDX ID: {license_info.spdx_id}")
