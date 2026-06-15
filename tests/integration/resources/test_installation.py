"""Test cases for Installation resource operations.

Tests GET operations for Installation resources.
Installations are read-only resources managed by platform integrations.
"""

import pytest

import endorlabs
from endorlabs.core.types import ListParameters
from tests.conftest import (
    TEST_MAX_PAGES,
    TEST_MAX_PAGES_TRAVERSE,
    TEST_PAGE_SIZE,
)


@pytest.mark.integration
class TestInstallation:
    """Test cases for Installation resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace, root_namespace) -> None:
        """Fast setup: client and namespace from conftest."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.tenant_root = root_namespace
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.endor_root_client = endorlabs.Client(
            tenant=root_namespace, api_client=api_client
        )

    @pytest.fixture
    def sample_installation(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Lists in namespace to find all namespaces, matching the
        pattern used in test_installation_list.
        """
        from endorlabs.core.exceptions import ServerError

        try:
            results = self.endor_root_client.Installation.list(
                list_params=ListParameters(page_size=TEST_PAGE_SIZE),
                max_pages=TEST_MAX_PAGES_TRAVERSE,
                traverse=True,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    def test_installation_list(self) -> None:
        """LIST in namespace (traverse when child namespaces hold installations)."""
        result = self.endor_root_client.Installation.list(
            max_pages=TEST_MAX_PAGES_TRAVERSE,
            traverse=True,
        )
        assert isinstance(result, list)

    def test_installation_get(self) -> None:
        """GET first item from LIST in namespace."""
        items = self.endor_root_client.Installation.list(
            max_pages=TEST_MAX_PAGES_TRAVERSE,
            traverse=True,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        got = self.endor_root_client.Installation.get(item)
        assert got is not None
        assert got.uuid == item.uuid

    def test_installation_filter_by_platform(self, sample_installation) -> None:
        """Test filtering installations by platform type."""
        print("\n=== TESTING FILTER INSTALLATIONS BY PLATFORM ===")

        # Get first installation to extract platform type
        first_installation = sample_installation
        if not first_installation.spec or not first_installation.spec.platform_type:
            pytest.skip("Installation has no platform_type")

        platform_type = first_installation.spec.platform_type
        # API expects the enum string value (e.g. PLATFORM_SOURCE_GITHUB), not the
        # Python enum name (e.g. PlatformSourceType.GITHUB).
        platform_type_value = (
            platform_type.value
            if hasattr(platform_type, "value")
            else str(platform_type)
        )

        # Scope filter to the sampled resource namespace to avoid broad traversal.
        list_namespace = (
            first_installation.tenant_meta.namespace
            if first_installation.tenant_meta
            and getattr(first_installation.tenant_meta, "namespace", None)
            else self.root_namespace
        )
        list_params = ListParameters(
            filter=f'spec.platform_type=="{platform_type_value}"',
            page_size=TEST_PAGE_SIZE,
        )

        list_client = endorlabs.Client(tenant=list_namespace, api_client=self.client)
        filtered_results = list_client.Installation.list(
            list_params=list_params,
            max_pages=TEST_MAX_PAGES,
        )

        assert isinstance(filtered_results, list), (
            "Should return a list of filtered installations"
        )
        if len(filtered_results) == 0:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

        # Verify all results have the same platform (compare by API value)
        for result in filtered_results:
            if result.spec and result.spec.platform_type:
                result_value = (
                    result.spec.platform_type.value
                    if hasattr(result.spec.platform_type, "value")
                    else str(result.spec.platform_type)
                )
                assert result_value == platform_type_value, (
                    "All filtered results should have the same platform"
                )

        print(
            f"Found {len(filtered_results)} installations for platform "
            f"{platform_type_value}"
        )

    def test_installation_error_handling(self) -> None:
        """Test error handling for invalid UUID."""
        # Test with invalid UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endorlabs.core.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            self.endor_root_client.Installation.get("invalid-uuid")
        assert exc_info.value.resource_uuid == "invalid-uuid"
        assert exc_info.value.operation == "get"
        assert exc_info.value.status_code == 400
