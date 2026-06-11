"""Pytest configuration and shared constants for Endor Labs SDK tests.

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

# Log-style integration list profile (AuditLog, FindingLog, AuthenticationLog, …).
# Cap client fetches with max_pages only — do not force page_size=1; tiny page sizes
# can make log lists pathologically slow on the backend (see list-query-performance.md).
TEST_LOG_LIST_MAX_PAGES = 1
# Safety cap on rows returned in a single bounded list (one default-sized page).
TEST_LOG_LIST_MAX_ROWS = 100

# ScanLogRequest / get_scan_result_logs: cap returned log lines in tests.
TEST_SCAN_LOG_MAX_ENTRIES = 10

# Optional debug tests that iterate namespaces (off by default in CI).
TEST_LOG_DEBUG_MAX_NAMESPACES = 3
# Single source for test namespace: use env ENDOR_NAMESPACE or this default.
# Tests should use the `namespace` fixture (or this constant) instead of
# hardcoding a default. See docs/contributing/integration-resource-tests.md
# and troubleshooting.md.
TEST_NAMESPACE_DEFAULT = "endor-solutions-tgowan.tgowan-endor"

# Canonical GitHub remote for this repository (post-move: endorlabs/endorlabs-sdk).
CANONICAL_SDK_REPO_SLUG = "endorlabs/endorlabs-sdk"
CANONICAL_SDK_REPO_URL = f"https://github.com/{CANONICAL_SDK_REPO_SLUG}.git"


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


# ---------------------------------------------------------------------------
# Test cleanup constants
# Used only by test cleanup scripts — not by the SDK itself.
# ---------------------------------------------------------------------------

DEFAULT_TEST_TAGS = [
    "test",
    "dummy",
    "crud-test",
    "integration-test",
    "ml-finding",
]

TEST_API_KEY_NAMES = frozenset({"test-client-ux-api-key", "test-client-ux-api-key-del"})
TEST_SCAN_PROFILE_PREFIXES = (
    "client-ux-profile-",
    "client-ux-update-",
    "client-ux-del-",
    "test-profile-",
)
TEST_NAMESPACE_PREFIXES = (
    "mock-namespace-",
    "client-ux-ns-",
    "client-ux-del-ns-",
    "test-update-ns-",
)
TEST_SEMGREP_RULE_PREFIXES = (
    "client-ux-rule-",
    "client-ux-update-",
    "client-ux-del-",
)
TEST_AUTHORIZATION_POLICY_PREFIXES = (
    "client-ux-auth-",
    "client-ux-update-",
    "client-ux-del-",
)
TEST_POLICY_NAME_PREFIXES = (
    "Test Exception Policy ",
    "Test Notification Policy ",
    "Test Admission Policy ",
    "ClientUX Exception ",
    "ClientUX Del ",
)


@pytest.fixture(autouse=True)
def setup_logging() -> None:
    """Setup logging for tests."""
    logging.basicConfig(level=logging.DEBUG)
