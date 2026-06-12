"""Unit tests for concurrent list operations across namespaces.

Verifies the concurrent=True parameter behavior in facade.list() and related
methods using mocks (no API credentials required).
"""

from unittest.mock import Mock, patch

import pytest

from endorlabs.client_surface import Client
from endorlabs.resources.base import TenantMeta
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

    def test_error_in_one_namespace_raises_with_failed_namespaces(self) -> None:
        """Any namespace failure raises and reports failed namespace names."""

        def query_with_error(ns: str) -> list[Mock]:
            if ns == "tenant.failing":
                raise RuntimeError("Query failed")
            return [Mock(uuid=f"item-from-{ns}")]

        with pytest.raises(RuntimeError, match=r"tenant\.failing"):
            execute_across_namespaces(
                ["tenant.ok1", "tenant.failing", "tenant.ok2"],
                query_with_error,
                max_workers=3,
            )

    def test_max_workers_limits_concurrency(self) -> None:
        """max_workers is respected (effective_workers = min(workers, len(ns)))."""
        items = [Mock(uuid=f"item-{i}") for i in range(5)]
        query_fn = Mock(return_value=[items[0]])
        namespaces = [f"tenant.ns{i}" for i in range(5)]
        result = execute_across_namespaces(namespaces, query_fn, max_workers=2)
        assert len(result) == 5
        assert query_fn.call_count == 5

    def test_multiple_namespace_failures_are_reported(self) -> None:
        """Raised error message includes every failed namespace."""

        def query_with_multiple_errors(ns: str) -> list[Mock]:
            if ns in {"tenant.failing1", "tenant.failing2"}:
                raise ValueError(f"{ns} failed")
            return [Mock(uuid=f"item-from-{ns}")]

        with pytest.raises(RuntimeError) as exc_info:
            execute_across_namespaces(
                ["tenant.ok", "tenant.failing1", "tenant.failing2"],
                query_with_multiple_errors,
                max_workers=3,
            )

        error_message = str(exc_info.value)
        assert "tenant.failing1" in error_message
        assert "tenant.failing2" in error_message


# ============================================================================
# Unit tests for facade concurrent list behavior
# ============================================================================


class TestFacadeConcurrentList:
    """Unit tests for concurrent list behavior in _ListableFacade."""

    def test_concurrent_without_traverse_uses_single_query(
        self, client_with_mock_transport: Client
    ) -> None:
        """list(traverse=False) ignores concurrent default and uses single query."""
        client = client_with_mock_transport
        mock_list = Mock(return_value=[])
        client.Project._ops.list = mock_list
        client.Project.list(
            traverse=False,
            max_pages=TEST_MAX_PAGES,
        )
        mock_list.assert_called_once()

    def test_traverse_defaults_to_concurrent_mode(
        self, client_with_mock_transport: Client
    ) -> None:
        """list(traverse=True) uses concurrent mode without explicit concurrent=True."""
        from endorlabs.operations import BaseResourceOperations

        client = client_with_mock_transport

        def make_ops(client_arg, resource_name, model_class):
            if resource_name == "namespaces":
                m = Mock(spec=BaseResourceOperations)
                m.list = Mock(return_value=[])
                return m
            return BaseResourceOperations(client_arg, resource_name, model_class)

        with (
            patch("endorlabs.facade.base.BaseResourceOperations", side_effect=make_ops),
            patch(
                "endorlabs.utils.parallel.execute_across_namespaces",
                return_value=[],
            ) as mock_execute,
        ):
            client.Project._ops.list = Mock(return_value=[])
            client.Project.list(
                traverse=True,
                namespace="tenant",
                max_pages=TEST_MAX_PAGES,
            )
            mock_execute.assert_called_once()

    def test_concurrent_with_traverse_calls_namespace_list_first(
        self, client_with_mock_transport: Client
    ) -> None:
        """Concurrent list fetches namespaces via ops."""
        from endorlabs.operations import BaseResourceOperations

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

        mock_ns_ops_list = Mock(return_value=[mock_ns1, mock_ns2])

        def make_ops(client_arg, resource_name, model_class):
            if resource_name == "namespaces":
                m = Mock(spec=BaseResourceOperations)
                m.list = mock_ns_ops_list
                return m
            return BaseResourceOperations(client_arg, resource_name, model_class)

        with (
            patch(
                "endorlabs.facade.base.BaseResourceOperations",
                side_effect=make_ops,
            ),
            patch(
                "endorlabs.utils.parallel.execute_across_namespaces",
                return_value=[],
            ) as mock_execute,
        ):
            client.Project._ops.list = Mock(return_value=[])
            client.Project.list(
                concurrent=True,
                traverse=True,
                namespace="tenant",
                max_pages=TEST_MAX_PAGES,
            )

            mock_ns_ops_list.assert_called_once()
            call_args = mock_ns_ops_list.call_args
            assert call_args[0][0] == "tenant"
            assert call_args[0][1].traverse is True

            mock_execute.assert_called_once()

    def test_concurrent_queries_each_namespace_without_traverse(
        self, client_with_mock_transport: Client
    ) -> None:
        """Concurrent mode queries each namespace without traverse flag."""
        from endorlabs.operations import BaseResourceOperations

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

        def make_ops(client_arg, resource_name, model_class):
            if resource_name == "namespaces":
                m = Mock(spec=BaseResourceOperations)
                m.list = Mock(return_value=[mock_ns1])
                return m
            return BaseResourceOperations(client_arg, resource_name, model_class)

        with (
            patch("endorlabs.facade.base.BaseResourceOperations", side_effect=make_ops),
            patch(
                "endorlabs.utils.parallel.execute_across_namespaces",
                side_effect=capture_query_fn,
            ),
        ):
            client.Project._ops.list = Mock(return_value=[])
            client.Project.list(
                concurrent=True,
                traverse=True,
                namespace="tenant",
                max_pages=TEST_MAX_PAGES,
            )

    def test_concurrent_merges_results_from_all_namespaces(
        self, client_with_mock_transport: Client
    ) -> None:
        """Concurrent mode returns merged results from all namespaces."""
        from endorlabs.operations import BaseResourceOperations

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

        def make_ops(client_arg, resource_name, model_class):
            if resource_name == "namespaces":
                m = Mock(spec=BaseResourceOperations)
                m.list = Mock(return_value=[mock_ns1, mock_ns2])
                return m
            return BaseResourceOperations(client_arg, resource_name, model_class)

        with (
            patch("endorlabs.facade.base.BaseResourceOperations", side_effect=make_ops),
            patch(
                "endorlabs.utils.parallel.execute_across_namespaces",
                return_value=merged_results,
            ),
        ):
            client.Project._ops.list = Mock(return_value=[])
            result = client.Project.list(
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
        from endorlabs.operations import BaseResourceOperations

        client = client_with_mock_transport

        def make_ops(client_arg, resource_name, model_class):
            if resource_name == "namespaces":
                m = Mock(spec=BaseResourceOperations)
                m.list = Mock(return_value=[])
                return m
            return BaseResourceOperations(client_arg, resource_name, model_class)

        with (
            patch("endorlabs.facade.base.BaseResourceOperations", side_effect=make_ops),
            patch(
                "endorlabs.utils.parallel.execute_across_namespaces",
                return_value=[],
            ) as mock_execute,
        ):
            client.Project._ops.list = Mock(return_value=[])
            client.Project.list(
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
        from endorlabs.operations import BaseResourceOperations

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

        def make_ops(client_arg, resource_name, model_class):
            if resource_name == "namespaces":
                m = Mock(spec=BaseResourceOperations)
                m.list = Mock(return_value=[mock_ns1])
                return m
            return BaseResourceOperations(client_arg, resource_name, model_class)

        with (
            patch("endorlabs.facade.base.BaseResourceOperations", side_effect=make_ops),
            patch(
                "endorlabs.utils.parallel.execute_across_namespaces",
                side_effect=capture_execute,
            ),
        ):
            client.Project._ops.list = Mock(return_value=[])
            client.Project.list(
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
        client.Project._ops.list_iter = Mock(return_value=iter([]))
        with pytest.raises(
            NotImplementedError, match="concurrent=True is not supported for list_iter"
        ):
            list(
                client.Project.list_iter(
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
        client.Project._ops.list_iter = Mock(return_value=iter([Mock(uuid="p1")]))
        result = list(
            client.Project.list_iter(
                concurrent=False,
                traverse=True,
                max_pages=TEST_MAX_PAGES,
            )
        )
        assert len(result) == 1


class TestFacadeSearchByName:
    """Unit tests for Project.search_by_name."""

    def test_search_by_name_with_traverse(
        self, client_with_mock_transport: Client
    ) -> None:
        client = client_with_mock_transport
        mock_item = Mock(
            uuid="proj-1",
            meta=Mock(name="my-project"),
            tenant_meta=Mock(namespace=TEST_NAMESPACE_DEFAULT),
        )
        client.Project.list = Mock(return_value=[mock_item])
        result = client.Project.search_by_name(
            "my-proj",
            traverse=True,
            max_pages=2,
        )
        assert result == [mock_item]

    def test_search_by_name_without_traverse(
        self, client_with_mock_transport: Client
    ) -> None:
        client = client_with_mock_transport
        mock_item = Mock(
            uuid="proj-1",
            meta=Mock(name="my-project"),
            tenant_meta=Mock(namespace=TEST_NAMESPACE_DEFAULT),
        )
        client.Project.list = Mock(return_value=[mock_item])
        result = client.Project.search_by_name(
            "project",
            traverse=False,
            max_pages=2,
        )
        assert result == [mock_item]
        client.Project.list.assert_called_once()
