"""
Pytest configuration and fixtures for Endor Cockpit tests.

This module provides common fixtures and configuration for testing
the Endor Cockpit SDK across all modules.
"""

import logging
from typing import Any, Dict
from unittest.mock import Mock

import pytest

from endor_cockpit.api_client import APIClient


@pytest.fixture
def mock_client():
    """Create a mock APIClient for testing."""
    client = Mock(spec=APIClient)
    client.default_headers = {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    return client


@pytest.fixture
def sample_namespace():
    """Sample namespace for testing."""
    import os
    namespace = os.getenv("ENDOR_NAMESPACE", "test.tenant.namespace")
    return namespace


@pytest.fixture
def sample_project_data():
    """Sample project data for testing."""
    return {
        "uuid": "project-uuid-123",
        "meta": {
            "name": "https://github.com/org/repo.git",
            "description": "Test repository",
            "create_time": "2025-10-19T10:00:00Z",
            "created_by": "test@endor.ai",
            "tags": ["test", "example"],
        },
        "spec": {
            "git": {
                "full_name": "org/repo",
                "git_clone_url": "git@github.com:org/repo.git",
                "http_clone_url": "https://github.com/org/repo.git",
            },
            "platform_source": "PLATFORM_SOURCE_GITHUB",
        },
        "tenant_meta": {"namespace": "test.tenant.namespace"},
    }


@pytest.fixture
def sample_finding_data():
    """Sample finding data for testing."""
    return {
        "uuid": "finding-uuid-123",
        "meta": {
            "name": "vulnerability-finding-1",
            "description": "Test vulnerability finding",
            "create_time": "2025-10-19T10:00:00Z",
            "created_by": "test@endor.ai",
            "tags": ["security", "vulnerability"],
        },
        "spec": {
            "level": "FINDING_LEVEL_HIGH",
            "method": "SYSTEM_EVALUATION_METHOD_SCA",
            "ecosystem": "ECOSYSTEM_NPM",
            "finding_categories": ["FINDING_CATEGORY_VULNERABILITY"],
            "project_uuid": "project-uuid-123",
        },
        "tenant_meta": {"namespace": "test.tenant.namespace"},
    }


@pytest.fixture
def sample_policy_data():
    """Sample policy data for testing."""
    return {
        "uuid": "policy-uuid-123",
        "meta": {
            "name": "security-policy",
            "description": "Test security policy",
            "create_time": "2025-10-19T10:00:00Z",
            "created_by": "test@endor.ai",
            "tags": ["security", "policy"],
        },
        "spec": {
            "policy_type": "POLICY_TYPE_ML_FINDING",
            "rule": (
                "package security\n\nconfigure[result] {\n  result = {\n    "
                '"security_method": {\n      "disable": false\n    }\n  }\n}'
            ),
            "disable": False,
        },
        "tenant_meta": {"namespace": "test.tenant.namespace"},
    }


@pytest.fixture
def sample_namespace_data():
    """Sample namespace data for testing."""
    return {
        "uuid": "namespace-uuid-123",
        "meta": {
            "name": "test-namespace",
            "description": "Test namespace",
            "create_time": "2025-10-19T10:00:00Z",
            "created_by": "test@endor.ai",
            "tags": ["test", "namespace"],
        },
        "spec": {
            "parent_namespace": "test.tenant.namespace",
            "description": "Test namespace for development",
        },
        "tenant_meta": {"namespace": "test.tenant.namespace.test-namespace"},
    }


@pytest.fixture
def mock_api_response():
    """Mock API response for testing."""

    def _mock_response(data: Dict[str, Any], status_code: int = 200):
        response = Mock()
        response.status_code = status_code
        response.json.return_value = data
        response.text = str(data)
        return response

    return _mock_response


@pytest.fixture(autouse=True)
def setup_logging():
    """Setup logging for tests."""
    logging.basicConfig(level=logging.DEBUG)
    # Suppress schema drift warnings in tests
    logging.getLogger("endor_cockpit.utils.schema_drift").setLevel(logging.ERROR)


@pytest.fixture
def schema_drift_data():
    """Sample data with schema drift for testing."""
    return {
        "uuid": "test-uuid",
        "meta": {
            "name": "test-resource",
            "description": "Test resource",
            "unknown_field": "unknown_value",  # This should trigger schema drift
            "another_unknown": {"nested": "data"},
        },
        "spec": {
            "known_field": "known_value",
            "unknown_spec_field": "unknown_spec_value",
        },
        "tenant_meta": {"namespace": "test.namespace"},
    }
