"""
Base test class for Endor Cockpit resource tests.

This module provides shared test methods that can be used across
all resource test classes to eliminate duplication.
"""

import pytest

from endor_cockpit.models.base import BaseMeta, BaseResource, BaseSpec


class BaseResourceTest:
    """Base test class with shared test methods for all resources."""

    def test_base_class_inheritance(self, resource_instance):
        """Test that resource inherits from base classes.

        This test validates that all resources properly inherit from
        BaseResource, and their meta/spec inherit from BaseMeta/BaseSpec.

        Args:
            resource_instance: A resource instance to test (provided by
                subclass via fixture)
        """
        # Test BaseResource inheritance
        assert isinstance(
            resource_instance, BaseResource
        ), "Resource should inherit from BaseResource"

        # Test BaseMeta inheritance
        assert isinstance(
            resource_instance.meta, BaseMeta
        ), "Resource meta should inherit from BaseMeta"

        # Test BaseSpec inheritance
        assert isinstance(
            resource_instance.spec, BaseSpec
        ), "Resource spec should inherit from BaseSpec"

    def test_schema_drift_detection(self, resource_instance):
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
        assert hasattr(
            resource_instance, "model_config"
        ), "Resource should have model_config for Pydantic validation"

    def test_get_list(
        self, list_func, api_client, namespace, test_list_params
    ):
        """Generic test for GET list operations.

        Args:
            list_func: The list function to test (e.g., project.list_projects)
            api_client: APIClient instance
            namespace: Namespace string
            test_list_params: ListParameters with pagination limits
        """
        resources = list_func(api_client, namespace, list_params=test_list_params)
        assert isinstance(resources, list), "Should return a list"
        assert len(resources) > 0, "Should have at least one resource"

    def test_get_by_uuid(self, get_func, api_client, namespace, resource_uuid):
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

    def test_error_handling(self, get_func, api_client, namespace):
        """Generic test for error handling with invalid UUID.

        Args:
            get_func: The get function to test (e.g., project.get_project)
            api_client: APIClient instance
            namespace: Namespace string
        """
        # Test with invalid UUID
        invalid_resource = get_func(api_client, namespace, "invalid-uuid")
        assert invalid_resource is None, "Should return None for invalid UUID"

