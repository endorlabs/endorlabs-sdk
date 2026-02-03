"""Shared constants for maneuver scripts.

This module defines common constants used across multiple maneuver scripts,
including default page sizes and test tag lists.
"""

# Default page sizes for API pagination
DEFAULT_PAGE_SIZE = 100
LARGE_PAGE_SIZE = 500
SMALL_PAGE_SIZE = 5

# Default test tags for cleanup operations
# These can be overridden via CLI arguments
DEFAULT_TEST_TAGS = [
    "test",
    "dummy",
    "crud-test",
    "integration-test",
    "ml-finding",
]

# Test-only name criteria for cleanup_test_resources.py (do not delete others)
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
# Policy: tag in test set AND name starts with one of these (see cleanup_test_policies)
TEST_POLICY_NAME_PREFIXES = (
    "Test Exception Policy ",
    "Test Notification Policy ",
    "Test Admission Policy ",
    "ClientUX Exception ",
    "ClientUX Del ",
)
