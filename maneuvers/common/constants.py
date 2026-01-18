"""
Shared constants for maneuver scripts.

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
