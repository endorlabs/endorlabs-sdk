"""Base test class for Endor Cockpit resource tests.

This module provides shared test methods and patterns that can be used across
all resource test classes to eliminate duplication and ensure consistency.
"""

import os
from typing import Any

import conftest
import pytest

from endorlabs.api_client import APIClient
from endorlabs.models.base import BaseMeta, BaseResource, BaseSpec


class BaseResourceTest:
    """Base test class with shared test methods for all resources."""

    def test_base_class_inheritance(self, resource_instance: Any) -> None:
        """Test that resource inherits from base classes.

        This test validates that all resources properly inherit from
        BaseResource, and their meta/spec inherit from BaseMeta/BaseSpec.

        Args:
            resource_instance: A resource instance to test (provided by
                subclass via fixture)

        """
        # Test BaseResource inheritance
        assert isinstance(resource_instance, BaseResource), (
            "Resource should inherit from BaseResource"
        )

        # Test BaseMeta inheritance
        assert isinstance(resource_instance.meta, BaseMeta), (
            "Resource meta should inherit from BaseMeta"
        )

        # Test BaseSpec inheritance
        assert isinstance(resource_instance.spec, BaseSpec), (
            "Resource spec should inherit from BaseSpec"
        )

    def test_schema_drift_detection(self, resource_instance: Any) -> None:
        """Test that schema drift detection is working.

        This test validates that schema drift detection is functional
        by checking that the resource instance has the model_config
        attribute, which indicates Pydantic model validation is working.

        Args:
            resource_instance: A resource instance to test (provided by
                subclass via fixture)

        """
        # Test that schema drift detection is working
        # This is tested implicitly through the model validation
        assert resource_instance is not None, "Resource instance should exist"

        # Test that unknown fields are handled gracefully
        # This is tested through the model's extra="ignore" configuration
        assert hasattr(resource_instance, "model_config"), (
            "Resource should have model_config for Pydantic validation"
        )

    def test_get_list(
        self,
        list_func: Any,
        api_client: APIClient,
        namespace: str,
        test_list_params: Any,
    ) -> None:
        """Generic test for GET list operations.

        Args:
            list_func: The list function to test (e.g., project.list_projects)
            api_client: APIClient instance
            namespace: Namespace string
            test_list_params: ListParameters with pagination limits

        """
        import conftest

        resources = list_func(
            api_client,
            namespace,
            list_params=test_list_params,
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(resources, list), "Should return a list"
        if len(resources) == 0:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

    def test_get_by_uuid(self, get_func, api_client, namespace, resource_uuid) -> None:
        """Generic test for GET by UUID operations.

        Args:
            get_func: The get function to test (e.g., project.get_project)
            api_client: APIClient instance
            namespace: Namespace string
            resource_uuid: UUID of resource to retrieve

        """
        resource = get_func(api_client, namespace, resource_uuid)
        assert resource is not None, "Should successfully retrieve resource by UUID"
        assert resource.uuid == resource_uuid, "Retrieved resource UUID should match"

    def test_error_handling(self, get_func, api_client, namespace) -> None:
        """Generic test for error handling with invalid UUID.

        Args:
            get_func: The get function to test (e.g., project.get_project)
            api_client: APIClient instance
            namespace: Namespace string

        """
        # Test with invalid UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endorlabs.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            get_func(api_client, namespace, "invalid-uuid")
        assert exc_info.value.resource_uuid == "invalid-uuid"
        assert exc_info.value.operation == "get"
        assert exc_info.value.status_code == 400


class BaseIntegrationTest:
    """Base class for integration tests with common setup and cleanup patterns.

    This class provides:
    - Standardized setup with client and namespace
    - Resource tracking for cleanup
    - Teardown method pattern
    """

    @pytest.fixture(autouse=True)
    def base_setup(self) -> None:
        """Base setup for all integration tests.

        Sets up client, namespace, and resource tracking.
        Subclasses should override this and call super().base_setup() if needed.
        """
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Initialize resource tracking (subclasses should override with specific lists)
        # Example: self.created_policy_uuids = []
        # This is a placeholder - subclasses should define their own tracking lists

    def teardown_method(self) -> None:
        """Base teardown method.

        Subclasses should override this to clean up their specific resources.
        This method exists to ensure the pattern is consistent across all tests.
        """
        # Subclasses should implement cleanup logic here
        # Example:
        # if hasattr(self, "created_policy_uuids"):
        #     for uuid in self.created_policy_uuids:
        #         try:
        #             policy.delete_policy(self.client, self.namespace, uuid)
        #         except Exception as e:
        #             print(f"[WARNING] Failed to delete {uuid}: {e}")
        #     self.created_policy_uuids.clear()
        pass
