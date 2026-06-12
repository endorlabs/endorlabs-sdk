"""Fixtures for unit tests (no API credentials required).

All fixtures here use mocks or hardcoded values. No real APIClient
is constructed, so these tests run without ENDOR_* environment variables.
"""

import os
from typing import Any
from unittest.mock import Mock

import pytest

from endorlabs.api_client import APIClient
from endorlabs.core.types import ListParameters
from tests.conftest import TEST_PAGE_SIZE


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
    """Sample namespace for testing (no skip when unset; use for mocks)."""
    return os.getenv("ENDOR_NAMESPACE", "test.tenant.namespace")


@pytest.fixture
def test_list_params():
    """Create ListParameters with test pagination limits."""
    return ListParameters(page_size=TEST_PAGE_SIZE)


@pytest.fixture
def mock_api_response():
    """Mock API response for testing."""

    def _mock_response(data: dict[str, Any], status_code: int = 200):
        response = Mock()
        response.status_code = status_code
        response.json.return_value = data
        response.text = str(data)
        return response

    return _mock_response
