"""Fixtures and configuration for integration tests (require API credentials).

CI runs all integration tests (including those that perform writes) using admin
credentials on the isolated root namespace. Tests that create/update/delete are
marked @pytest.mark.writes for optional selective runs
(e.g. -m "integration and not writes" for read-only; -m "writes" for write-only).
"""

import os

import pytest

import endorlabs
from endorlabs.api_client import APIClient
from endorlabs.core.types import ListParameters
from tests.conftest import (
    TEST_LOG_LIST_MAX_PAGES,
    TEST_LOG_LIST_MAX_ROWS,
    TEST_NAMESPACE_DEFAULT,
)


def log_list_kwargs() -> dict[str, int]:
    """Facade list() kwargs for log integration tests: max_pages only (no page_size)."""
    return {"max_pages": TEST_LOG_LIST_MAX_PAGES}


def bounded_log_list_params(
    *,
    filter_expr: str | None = None,
    sort_by: str | None = None,
    desc: bool | None = None,
) -> ListParameters:
    """Bounded ListParameters for log-style integration lists (no traverse, no page_size)."""
    kwargs: dict[str, object] = {}
    if filter_expr is not None:
        kwargs["filter"] = filter_expr
    if sort_by is not None:
        kwargs["sort_by"] = sort_by
    if desc is not None:
        kwargs["desc"] = desc
    return ListParameters(**kwargs)


def assert_bounded_log_rows(rows: list[object]) -> None:
    """Assert SDK list stayed within log integration pagination caps."""
    assert len(rows) <= TEST_LOG_LIST_MAX_ROWS


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------


def _has_credentials() -> bool:
    """Check if Endor Labs API key credentials are available.

    ``ENDOR_API`` is optional; ``APIClient`` defaults to production when unset.
    Tests only support API key authentication, not browser-based auth.
    """
    return bool(
        os.getenv("ENDOR_API_CREDENTIALS_KEY")
        and os.getenv("ENDOR_API_CREDENTIALS_SECRET")
    )


def _needs_live_api_credentials(item: pytest.Item) -> bool:
    """True when a test requires API key auth (marker or live-api fixtures)."""
    if "integration" in item.keywords:
        return True
    live_api_fixtures = frozenset(
        {
            "api_client",
            "api_client_fast_retry",
            "endor_client",
            "endor_root_client",
            "requires_credentials",
            "integration_config",
        }
    )
    return bool(live_api_fixtures & set(getattr(item, "fixturenames", ())))


def pytest_collection_modifyitems(config, items) -> None:
    """Mark integration tests and skip live-API tests when credentials are absent."""
    del config
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        if not _has_credentials() and _needs_live_api_credentials(item):
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

    Integration LIST operations can be slow on large traversals; use one retry
    and a long request timeout to balance resiliency with bounded retry loops.
    """
    client = APIClient(
        auth_method="api-key",
        max_retries=1,
        timeout=1800.0,  # 30 minutes
    )
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
        max_retries=1,
        backoff_factor=0.1,
        timeout=1800.0,  # Keep consistency with integration LIST behavior.
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
    """Tenant root (first segment of namespace).

    Use for traverse/concurrent list tests in tests/integration/client/test_concurrent_list.py.
    Per-resource integration tests list in the leaf namespace without traverse.
    """
    parts = namespace.split(".", 1)
    return parts[0] if len(parts) > 1 else namespace


@pytest.fixture
def endor_client(api_client, namespace):
    """Client facade scoped to the test namespace.

    Wraps the APIClient with the high-level Client surface so integration tests
    can call ``client.ResourceKind.list()`` etc. (PascalCase, endorctl-aligned).
    """
    return endorlabs.Client(tenant=namespace, api_client=api_client)


@pytest.fixture
def endor_root_client(api_client, root_namespace):
    """Client facade scoped to the tenant root for traverse operations."""
    return endorlabs.Client(tenant=root_namespace, api_client=api_client)


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
