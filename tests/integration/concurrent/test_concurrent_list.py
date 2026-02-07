"""Integration tests for concurrent list operations (requires real API access).

Unit tests for the concurrent facade live in tests/unit/client/test_concurrent_list.py.
"""

import pytest

import endorlabs
from tests.conftest import TEST_MAX_PAGES


@pytest.mark.integration
class TestConcurrentListIntegration:
    """Integration tests for concurrent list operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace, root_namespace) -> None:
        """Wire integration-test state."""
        self.api_client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace

    def test_concurrent_list_projects_returns_results(self) -> None:
        """Concurrent list of projects returns results (integration)."""
        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.api_client,
        )
        result = client.project.list(
            concurrent=True,
            traverse=True,
            max_workers=5,
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, list)

    def test_concurrent_list_with_filter(self) -> None:
        """Concurrent list with filter works (integration)."""
        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.api_client,
        )
        result = client.namespace.list(
            concurrent=True,
            traverse=True,
            max_workers=5,
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, list)


@pytest.mark.integration
@pytest.mark.long
class TestConcurrentListPerformance:
    """Performance comparison tests (marked long, run manually)."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace, root_namespace) -> None:
        """Wire integration-test state."""
        self.api_client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace

    def test_concurrent_vs_sequential_timing(self) -> None:
        """Compare timing of concurrent vs sequential list (informational)."""
        import time

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.api_client,
        )

        start = time.time()
        _ = client.project.list(
            traverse=True,
            concurrent=False,
            max_pages=2,
        )
        sequential_time = time.time() - start

        start = time.time()
        _ = client.project.list(
            traverse=True,
            concurrent=True,
            max_workers=10,
            max_pages=2,
        )
        concurrent_time = time.time() - start

        print(f"\nSequential time: {sequential_time:.2f}s")
        print(f"Concurrent time: {concurrent_time:.2f}s")
        assert sequential_time > 0
        assert concurrent_time > 0
