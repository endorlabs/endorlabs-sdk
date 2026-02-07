"""Pytest configuration and shared constants for Endor Cockpit tests.

Root conftest: environment loading, logging setup, and constants shared
across both unit and integration test suites.
"""

import logging
import os
from pathlib import Path

import pytest

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
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    quoted = (value.startswith('"') and value.endswith('"')) or (
                        value.startswith("'") and value.endswith("'")
                    )
                    if quoted:
                        value = value[1:-1]
                    if key and not os.getenv(key):
                        os.environ[key] = value


@pytest.fixture(autouse=True)
def setup_logging() -> None:
    """Setup logging for tests."""
    logging.basicConfig(level=logging.DEBUG)
    # Suppress schema drift warnings in tests
    logging.getLogger("endorlabs.utils.schema_drift").setLevel(logging.ERROR)
