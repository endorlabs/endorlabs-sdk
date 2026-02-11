"""Shared fixtures for tests/unit/client/ (no API credentials required).

Consolidates the ``client_with_mock_transport`` fixture that was previously
duplicated across test_client_facade.py and test_concurrent_list.py.
"""

from unittest.mock import Mock

import pytest

import endorlabs
from endorlabs.api_client import APIClient
from endorlabs.client_surface import Client
from tests.conftest import TEST_NAMESPACE_DEFAULT


@pytest.fixture
def client_with_mock_transport() -> Client:
    """Client with mock APIClient and canonical test namespace."""
    mock = Mock(spec=APIClient)
    return endorlabs.Client(api_client=mock, tenant=TEST_NAMESPACE_DEFAULT)
