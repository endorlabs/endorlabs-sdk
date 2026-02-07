"""Fixtures and configuration for integration tests (require API credentials).

CI runs all integration tests (including those that perform writes) using admin
credentials on the isolated root namespace. Tests that create/update/delete are
marked @pytest.mark.writes for optional selective runs
(e.g. -m "integration and not writes" for read-only; -m "writes" for write-only).
"""

import os
import shutil

import pytest

from endorlabs.api_client import APIClient
from tests.conftest import TEST_NAMESPACE_DEFAULT

# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------


def _has_credentials() -> bool:
    """Check if Endor Labs API key credentials are available.

    Tests only support API key authentication, not browser-based auth.
    """
    required_vars = [
        "ENDOR_API",
        "ENDOR_API_CREDENTIALS_KEY",
        "ENDOR_API_CREDENTIALS_SECRET",
    ]
    return all(os.getenv(var) for var in required_vars)


def pytest_collection_modifyitems(config, items) -> None:
    """Skip integration tests when credentials are absent."""
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        if not _has_credentials() and "integration" in item.nodeid:
            item.add_marker(
                pytest.mark.skip(reason="No Endor Labs credentials available")
            )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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

    Same lifecycle as api_client: closed after the test finishes.
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


# ---------------------------------------------------------------------------
# Session-scoped helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def integration_config():
    """Integration test configuration."""
    ns = os.getenv("ENDOR_NAMESPACE", TEST_NAMESPACE_DEFAULT)
    if not ns:
        pytest.skip("ENDOR_NAMESPACE environment variable must be set")
    return {
        "tenant_namespace": ns,
        "test_prefix": "integration-test",
        "cleanup_delay": 1,
        "timeout": 60,
    }


@pytest.fixture(scope="session")
def requires_credentials() -> bool:
    """Fixture that requires valid credentials."""
    if not _has_credentials():
        pytest.skip("Endor Labs credentials not available")
    return True


@pytest.fixture(scope="session")
def requires_endorctl() -> bool:
    """Fixture that requires endorctl to be installed."""
    if not shutil.which("endorctl"):
        pytest.skip("endorctl not found - install endorctl to run security tests")
    return True
