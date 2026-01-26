"""
Configuration for integration tests.

This file provides fixtures and configuration for integration tests
that use the real Endor Labs API.
"""

import os

import pytest


def pytest_configure(config):
    """Configure pytest for integration tests."""
    # Add integration test marker
    config.addinivalue_line("markers", "integration: mark test as integration test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle integration tests."""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        # Skip integration tests if no credentials
        if not _has_credentials():
            if "integration" in item.nodeid:
                item.add_marker(
                    pytest.mark.skip(reason="No Endor Labs credentials available")
                )


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


@pytest.fixture(scope="session")
def integration_config():
    """Integration test configuration."""
    # Default to endor-solutions-tgowan.tgowan-endor namespace for tests
    namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.tgowan-endor")
    if not namespace:
        pytest.skip("ENDOR_NAMESPACE environment variable must be set")
    return {
        "tenant_namespace": namespace,
        "test_prefix": "integration-test",
        "cleanup_delay": 1,  # seconds between operations
        "timeout": 60,  # seconds for operations
    }


@pytest.fixture(scope="session")
def requires_credentials():
    """Fixture that requires valid credentials."""
    if not _has_credentials():
        pytest.skip("Endor Labs credentials not available")
    return True


@pytest.fixture(scope="session")
def requires_endorctl():
    """Fixture that requires endorctl to be installed."""
    import shutil

    if not shutil.which("endorctl"):
        pytest.skip("endorctl not found - install endorctl to run security tests")
    return True
