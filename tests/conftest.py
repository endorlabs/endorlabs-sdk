"""Pytest configuration and fixtures for Endor Cockpit tests.

This module provides common fixtures and configuration for testing
the Endor Cockpit SDK across all modules.
"""

import logging
import os
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from endorlabs.api_client import APIClient
from endorlabs.types import ListParameters

# Test pagination limits: 1 page, 1 item per page (same limits for all list tests)
TEST_PAGE_SIZE = 1
TEST_MAX_PAGES = 1
TEST_TRAVERSE_PAGE_SIZE = 1
TEST_MAX_PAGES_TRAVERSE = 1
# Single source for test namespace: use env ENDOR_NAMESPACE or this default.
# Tests should use the `namespace` fixture (or this constant) instead of
# hardcoding a default. See docs/rules-of-engagement/resource-implementation.md
# (Phase 2b) and troubleshooting.md.
TEST_NAMESPACE_DEFAULT = "endor-solutions-tgowan.tgowan-endor"


def pytest_configure(config) -> None:
    """Load .env file before tests run to ensure environment variables are set.

    This hook only loads variables from .env if they're not already set in the
    environment. This ensures:
    - Local development: .env file is loaded if present
    - CI/CD: GitHub Actions Secrets/Variables take precedence (not overridden)
    - The .env file is in .gitignore, so it won't exist in CI anyway
    """
    env_file = Path(".env")
    if env_file.exists():
        # Load .env file manually if UV didn't load it automatically
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue
                # Parse KEY=VALUE format
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes if present
                    quoted = (value.startswith('"') and value.endswith('"')) or (
                        value.startswith("'") and value.endswith("'")
                    )
                    if quoted:
                        value = value[1:-1]
                    # Only set if not already in environment
                    # (CI variables take precedence)
                    if key and not os.getenv(key):
                        os.environ[key] = value


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
def api_client():
    """Create a real APIClient instance for integration tests.

    Uses API key authentication only (not browser auth).
    Client is closed after the test (or fixture consumer) finishes.
    """
    client = APIClient(auth_method="api-key")
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def api_client_fast_retry():
    """APIClient with reduced retries for faster test failure (e.g. api_key).

    Same lifecycle as api_client: closed after the test (or fixture consumer) finishes.
    """
    client = APIClient(
        auth_method="api-key",
        max_retries=2,
        backoff_factor=0.1,
    )
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def namespace():
    """Get namespace from environment for testing.

    Single source: uses ENDOR_NAMESPACE or conftest TEST_NAMESPACE_DEFAULT.
    Skips when unset (strict env-only: set ENDOR_NAMESPACE in CI).
    """
    ns = os.getenv("ENDOR_NAMESPACE", TEST_NAMESPACE_DEFAULT)
    if not ns:
        pytest.skip("ENDOR_NAMESPACE environment variable must be set")
    return ns


@pytest.fixture
def root_namespace(namespace):
    """Tenant root (first segment of namespace) for LIST with traverse.

    Use with client.list(traverse=True) so resources in the instance are captured.
    """
    parts = namespace.split(".", 1)
    return parts[0] if len(parts) > 1 else namespace


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


@pytest.fixture(autouse=True)
def setup_logging() -> None:
    """Setup logging for tests."""
    logging.basicConfig(level=logging.DEBUG)
    # Suppress schema drift warnings in tests
    logging.getLogger("endorlabs.utils.schema_drift").setLevel(logging.ERROR)


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
