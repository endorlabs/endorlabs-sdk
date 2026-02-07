"""Unit tests for concurrent list operations across namespaces.

Verifies the concurrent=True parameter behavior in facade.list() and related
methods using mocks (no API credentials required).
"""

from unittest.mock import Mock, patch

import pytest

import endorlabs
from endorlabs.api_client import APIClient
from endorlabs.client_surface import Client
from endorlabs.models.base import TenantMeta
from endorlabs.resources.namespace import Namespace, NamespaceMeta, NamespaceSpec
from endorlabs.utils.parallel import execute_across_namespaces
from tests.conftest import TEST_MAX_PAGES, TEST_NAMESPACE_DEFAULT

# ============================================================================
# Unit tests for execute_across_namespaces utility
# ============================================================================


class TestExecuteAcrossNamespaces:
    """Unit tests for the parallel execution utility."""

    def test_empty_namespaces_returns_empty_list(self) -> None:
        """execute_across_namespaces with empty list returns empty list."""
        query_fn = Mock(return_value=[])
        result = execute_across_namespaces([], query_fn, max_workers=2)
        assert result == []
        query_fn.assert_not_called()

    def test_single_namespace_queries_once(self) -> None:
        """execute_across_namespaces with one namespace calls query_fn once."""
        item = Mock(uuid="item-1")
        query_fn = Mock(return_value=[item])
        result = execute_across_namespaces(["tenant.ns1"], query_fn, max_workers=2)
        assert len(result) == 1
        assert result[0] is item
        query_fn.assert_called_once_with("tenant.ns1")

    def test_multiple_namespaces_queries_all(self) -> None:
        """execute_across_namespaces queries each namespace and merges results."""
        items = {
            "tenant.ns1": [Mock(uuid="item-1"), Mock(uuid="item-2")],
            "tenant.ns2": [Mock(uuid="item-3")],
            "tenant.ns3": [],
        }
        query_fn = Mock(side_effect=lambda ns: items[ns])
        result = execute_across_namespaces(
            ["tenant.ns1", "tenant.ns2", "tenant.ns3"],
            query_fn,
            max_workers=3,
        )
        assert len(result) == 3
        assert query_fn.call_count == 3

    def test_error_in_one_namespace_continues_with_others(self) -> None:
        """Logs errors but returns results from successful namespaces."""

        def query_with_error(ns: str) -> list[Mock]:
            if ns == "tenant.failing":
                raise RuntimeError("Query failed")
            return [Mock(uuid=f"item-from-{ns}")]

        result = execute_across_namespaces(
            ["tenant.ok1", "tenant.failing", "tenant.ok2"],
            query_with_error,
            max_workers=3,
        )
        # Should have 2 items from successful namespaces
        assert len(result) == 2

    def test_max_workers_limits_concurrency(self) -> None:
        """max_workers is respected (effective_workers = min(workers, len(ns)))."""
        items = [Mock(uuid=f"item-{i}") for i in range(5)]
        query_fn = Mock(return_value=[items[0]])
        namespaces = [f"tenant.ns{i}" for i in range(5)]
        result = execute_across_namespaces(namespaces, query_fn, max_workers=2)
        assert len(result) == 5
        assert query_fn.call_count == 5


# ============================================================================
# Unit tests for facade concurrent list behavior
# ============================================================================


@pytest.fixture
def client_with_mock_transport() -> Client:
    """Client with mock APIClient and canonical test namespace."""
    mock = Mock(spec=APIClient)
    client = endorlabs.Client(
        api_client=mock,
        tenant=TEST_NAMESPACE_DEFAULT,
    )
    return client


class TestFacadeConcurrentList:
    """Unit tests for concurrent list behavior in _ListableFacade."""

    def test_concurrent_without_traverse_raises_value_error(
        self, client_with_mock_transport: Client
    ) -> None:
        """list(concurrent=True, traverse=False) raises ValueError."""
        client = client_with_mock_transport
        client.project._list_fn = Mock(return_value=[])
        with pytest.raises(ValueError, match="concurrent=True requires traverse=True"):
            client.project.list(
                concurrent=True,
                traverse=False,
                max_pages=TEST_MAX_PAGES,
            )

    def test_concurrent_with_traverse_calls_namespace_list_first(
        self, client_with_mock_transport: Client
    ) -> None:
        """list(concurrent=True, traverse=True) first fetches all namespaces."""
        client = client_with_mock_transport

        mock_ns1 = Namespace(
            uuid="ns-1",
            meta=NamespaceMeta(name="child1"),
            spec=NamespaceSpec(full_name="tenant.child1"),
            tenant_meta=TenantMeta(namespace="tenant"),
        )
        mock_ns2 = Namespace(
            uuid="ns-2",
            meta=NamespaceMeta(name="child2"),
            spec=NamespaceSpec(full_name="tenant.child2"),
            tenant_meta=TenantMeta(namespace="tenant"),
        )

        with (
            patch(
                "endorlabs.resources.namespace.list_namespaces",
                return_value=[mock_ns1, mock_ns2],
            ) as mock_list_ns,
            patch(
                "endorlabs.utils.parallel.execute_across_namespaces",
                return_value=[],
            ) as mock_execute,
        ):
            client.project._list_fn = Mock(return_value=[])
            client.project.list(
                concurrent=True,
                traverse=True,
                namespace="tenant",
                max_pages=TEST_MAX_PAGES,
            )

            mock_list_ns.assert_called_once()
            call_args = mock_list_ns.call_args
            assert call_args[0][1] == "tenant"
            assert call_args[0][2].traverse is True

            mock_execute.assert_called_once()

    def test_concurrent_queries_each_namespace_without_traverse(
        self, client_with_mock_transport: Client
    ) -> None:
        """Concurrent mode queries each namespace without traverse flag."""
        client = client_with_mock_transport

        mock_ns1 = Namespace(
            uuid="ns-1",
            meta=NamespaceMeta(name="child1"),
            spec=NamespaceSpec(full_name="tenant.child1"),
            tenant_meta=TenantMeta(namespace="tenant"),
        )

        query_fn_calls: list[dict] = []

        def capture_query_fn(namespaces, query_fn, max_workers):
            query_fn_calls.extend({"namespace": ns} for ns in namespaces)
            return []

        with (
            patch(
                "endorlabs.resources.namespace.list_namespaces",
                return_value=[mock_ns1],
            ),
            patch(
                "endorlabs.utils.parallel.execute_across_namespaces",
                side_effect=capture_query_fn,
            ),
        ):
            client.project._list_fn = Mock(return_value=[])
            client.project.list(
                concurrent=True,
                traverse=True,
                namespace="tenant",
                max_pages=TEST_MAX_PAGES,
            )

    def test_concurrent_merges_results_from_all_namespaces(
        self, client_with_mock_transport: Client
    ) -> None:
        """Concurrent mode returns merged results from all namespaces."""
        client = client_with_mock_transport

        mock_ns1 = Namespace(
            uuid="ns-1",
            meta=NamespaceMeta(name="child1"),
            spec=NamespaceSpec(full_name="tenant.child1"),
            tenant_meta=TenantMeta(namespace="tenant"),
        )
        mock_ns2 = Namespace(
            uuid="ns-2",
            meta=NamespaceMeta(name="child2"),
            spec=NamespaceSpec(full_name="tenant.child2"),
            tenant_meta=TenantMeta(namespace="tenant"),
        )

        merged_results = [
            Mock(uuid="proj-1"),
            Mock(uuid="proj-2"),
            Mock(uuid="proj-3"),
        ]

        with (
            patch(
                "endorlabs.resources.namespace.list_namespaces",
                return_value=[mock_ns1, mock_ns2],
            ),
            patch(
                "endorlabs.utils.parallel.execute_across_namespaces",
                return_value=merged_results,
            ),
        ):
            client.project._list_fn = Mock(return_value=[])
            result = client.project.list(
                concurrent=True,
                traverse=True,
                namespace="tenant",
                max_pages=TEST_MAX_PAGES,
            )

            assert result == merged_results
            assert len(result) == 3

    def test_concurrent_passes_max_workers(
        self, client_with_mock_transport: Client
    ) -> None:
        """max_workers parameter is passed to execute_across_namespaces."""
        client = client_with_mock_transport

        with (
            patch(
                "endorlabs.resources.namespace.list_namespaces",
                return_value=[],
            ),
            patch(
                "endorlabs.utils.parallel.execute_across_namespaces",
                return_value=[],
            ) as mock_execute,
        ):
            client.project._list_fn = Mock(return_value=[])
            client.project.list(
                concurrent=True,
                traverse=True,
                namespace="tenant",
                max_workers=15,
                max_pages=TEST_MAX_PAGES,
            )

            mock_execute.assert_called_once()
            _, kwargs = mock_execute.call_args
            assert kwargs.get("max_workers") == 15

    def test_concurrent_passes_filter_to_each_namespace_query(
        self, client_with_mock_transport: Client
    ) -> None:
        """Filter is passed through to each namespace query."""
        client = client_with_mock_transport

        mock_ns1 = Namespace(
            uuid="ns-1",
            meta=NamespaceMeta(name="child1"),
            spec=NamespaceSpec(full_name="tenant.child1"),
            tenant_meta=TenantMeta(namespace="tenant"),
        )

        captured_query_fn = None

        def capture_execute(namespaces, query_fn, max_workers):
            nonlocal captured_query_fn
            captured_query_fn = query_fn
            return []

        with (
            patch(
                "endorlabs.resources.namespace.list_namespaces",
                return_value=[mock_ns1],
            ),
            patch(
                "endorlabs.utils.parallel.execute_across_namespaces",
                side_effect=capture_execute,
            ),
        ):
            client.project._list_fn = Mock(return_value=[])
            client.project.list(
                concurrent=True,
                traverse=True,
                namespace="tenant",
                filter='meta.create_time >= "2024-01-01"',
                max_pages=TEST_MAX_PAGES,
            )

            assert captured_query_fn is not None


class TestFacadeListIterConcurrent:
    """Unit tests for list_iter with concurrent parameter."""

    def test_list_iter_concurrent_raises_not_implemented(
        self, client_with_mock_transport: Client
    ) -> None:
        """list_iter(concurrent=True) raises NotImplementedError."""
        client = client_with_mock_transport
        client.project._list_iter_fn = Mock(return_value=iter([]))
        with pytest.raises(
            NotImplementedError, match="concurrent=True is not supported for list_iter"
        ):
            list(
                client.project.list_iter(
                    concurrent=True,
                    traverse=True,
                    max_pages=TEST_MAX_PAGES,
                )
            )

    def test_list_iter_without_concurrent_works(
        self, client_with_mock_transport: Client
    ) -> None:
        """list_iter(concurrent=False) works normally."""
        client = client_with_mock_transport
        client.project._list_iter_fn = Mock(return_value=iter([Mock(uuid="p1")]))
        result = list(
            client.project.list_iter(
                concurrent=False,
                traverse=True,
                max_pages=TEST_MAX_PAGES,
            )
        )
        assert len(result) == 1


class TestFacadeLookupConcurrent:
    """Unit tests for lookup with concurrent parameter."""

    def test_lookup_concurrent_passes_through_to_list(
        self, client_with_mock_transport: Client
    ) -> None:
        """lookup(concurrent=True, traverse=True) passes concurrent to list()."""
        client = client_with_mock_transport

        mock_item = Mock(
            uuid="proj-1",
            tenant_meta=Mock(namespace=TEST_NAMESPACE_DEFAULT),
        )

        mock_ns1 = Namespace(
            uuid="ns-1",
            meta=NamespaceMeta(name="child1"),
            spec=NamespaceSpec(full_name="tenant.child1"),
            tenant_meta=TenantMeta(namespace="tenant"),
        )

        with (
            patch(
                "endorlabs.resources.namespace.list_namespaces",
                return_value=[mock_ns1],
            ),
            patch(
                "endorlabs.utils.parallel.execute_across_namespaces",
                return_value=[mock_item],
            ),
        ):
            client.project._list_fn = Mock(return_value=[mock_item])
            result = client.project.lookup(
                concurrent=True,
                traverse=True,
                name="my-project",
                max_pages=2,
            )

            assert result is mock_item

    def test_lookup_concurrent_without_traverse_raises(
        self, client_with_mock_transport: Client
    ) -> None:
        """lookup(concurrent=True, traverse=False) raises ValueError via list()."""
        client = client_with_mock_transport
        client.project._list_fn = Mock(return_value=[])
        with pytest.raises(ValueError, match="concurrent=True requires traverse=True"):
            client.project.lookup(
                concurrent=True,
                traverse=False,
                name="my-project",
                max_pages=2,
            )
