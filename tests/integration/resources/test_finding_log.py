"""Test cases for FindingLog resource operations.

Tests GET, POST, and DELETE operations for FindingLog resources, including
filtering by operation type and finding UUID.

Greenfield alias unit tests live in tests/unit/models/test_greenfield_aliases.py.
"""

import pytest

import endorlabs
from endorlabs.api_client import APIClient
from tests.conftest import (
    TEST_MAX_PAGES,
    TEST_MAX_PAGES_TRAVERSE,
    TEST_NAMESPACE_DEFAULT,
    TEST_PAGE_SIZE,
    TEST_TRAVERSE_PAGE_SIZE,
)


@pytest.mark.integration
@pytest.mark.long
class TestFindingLog:
    """Test cases for FindingLog resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace, root_namespace) -> None:
        """Fast setup: client and namespace from conftest."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.tenant_root = root_namespace
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.endor_root_client = endorlabs.Client(
            tenant=root_namespace, api_client=api_client
        )
        self.created_finding_log_uuids = []

    def teardown_method(self) -> None:
        """Clean up any resources created during tests."""
        if hasattr(self, "created_finding_log_uuids"):
            for uuid in self.created_finding_log_uuids:
                try:
                    self.endor_client.finding_log.delete(uuid)
                except Exception as e:
                    print(f"Warning: Failed to delete finding log {uuid}: {e}")
            self.created_finding_log_uuids.clear()

    def test_finding_log_list(self) -> None:
        """LIST from tenant root with traverse (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        result = client.finding_log.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_finding_log_get(self) -> None:
        """GET first item from LIST (root + traverse) (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.finding_log.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.root_namespace
        )
        got = client.finding_log.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    @pytest.fixture
    def sample_finding_log(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Uses indexed spec.operation filter for fast retrieval — unfiltered
        finding-log list can timeout on large namespaces.
        """
        from endorlabs.exceptions import ServerError
        from endorlabs.types import ListParameters

        try:
            results = self.endor_client.finding_log.list(
                list_params=ListParameters(
                    filter="spec.operation==OPERATION_CREATE",
                    page_size=TEST_PAGE_SIZE,
                ),
                max_pages=TEST_MAX_PAGES,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    def test_finding_log_list_by_operation_create(self) -> None:
        """Test filtering finding logs by CREATE operation."""
        print("\n=== TESTING FILTER FINDING LOGS BY OPERATION CREATE ===")
        from endorlabs.exceptions import ServerError
        from endorlabs.types import ListParameters

        list_params = ListParameters(
            filter="spec.operation==OPERATION_CREATE",
            page_size=TEST_PAGE_SIZE,
            traverse=True,
        )

        try:
            logs = self.endor_root_client.finding_log.list(
                list_params=list_params,
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")

        assert isinstance(logs, list), "Should return a list of finding logs"
        print(f"Found {len(logs)} CREATE operation finding logs")

        # Validate all returned logs have CREATE operation
        for log in logs:
            assert (
                log.spec.operation == "OPERATION_CREATE"
                or str(log.spec.operation) == "OPERATION_CREATE"
            ), (
                f"FindingLog {log.uuid} should have CREATE operation, "
                f"got {log.spec.operation}"
            )

        if logs:
            print(f"Sample CREATE log: {logs[0].uuid} - {logs[0].meta.name}")

    def test_finding_log_list_by_operation_update(self) -> None:
        """Test filtering finding logs by UPDATE operation."""
        print("\n=== TESTING FILTER FINDING LOGS BY OPERATION UPDATE ===")
        from endorlabs.exceptions import ServerError
        from endorlabs.types import ListParameters

        list_params = ListParameters(
            filter="spec.operation==OPERATION_UPDATE",
            page_size=TEST_PAGE_SIZE,
            traverse=True,
        )

        try:
            logs = self.endor_root_client.finding_log.list(
                list_params=list_params,
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")

        assert isinstance(logs, list), "Should return a list of finding logs"
        print(f"Found {len(logs)} UPDATE operation finding logs")

        # Validate all returned logs have UPDATE operation
        for log in logs:
            assert (
                log.spec.operation == "OPERATION_UPDATE"
                or str(log.spec.operation) == "OPERATION_UPDATE"
            ), (
                f"FindingLog {log.uuid} should have UPDATE operation, "
                f"got {log.spec.operation}"
            )

        if logs:
            print(f"Sample UPDATE log: {logs[0].uuid} - {logs[0].meta.name}")

    def test_finding_log_get_and_finding_uuid(self, sample_finding_log) -> None:
        """Test GET by UUID and verify spec.finding_uuid is populated.

        Heuristic approach: instead of list+filter on the unindexed
        spec.finding_uuid field (which causes backend timeouts), we
        list with an indexed filter (spec.operation) via the
        sample_finding_log fixture, then GET by UUID and verify the
        finding_uuid field round-trips correctly.
        """
        print("\n=== TESTING GET FINDING LOG + FINDING UUID FIELD ===")

        ns = (
            sample_finding_log.tenant_meta.namespace
            if sample_finding_log.tenant_meta
            and getattr(sample_finding_log.tenant_meta, "namespace", None)
            else self.namespace
        )

        got = self.endor_client.finding_log.get(sample_finding_log.uuid, namespace=ns)

        assert got is not None, "GET should return a finding log"
        assert got.uuid == sample_finding_log.uuid, "UUID should match"
        assert got.spec is not None, "Spec should be present"
        assert got.spec.finding_uuid, (
            "spec.finding_uuid should be populated on a finding log"
        )
        assert got.spec.finding_uuid == sample_finding_log.spec.finding_uuid, (
            f"finding_uuid mismatch: GET returned {got.spec.finding_uuid}, "
            f"expected {sample_finding_log.spec.finding_uuid}"
        )

        print(
            f"GET finding log {got.uuid}: "
            f"finding_uuid={got.spec.finding_uuid}, "
            f"operation={got.spec.operation}"
        )

    def test_finding_log_traverse(self) -> None:
        """Test namespace traversal for finding logs with filter.

        Note: FindingLogs traverse without filter can timeout due to large
        dataset. This test uses a filter to limit the query scope.
        """
        print("\n=== TESTING FINDING LOG TRAVERSE ===")
        from endorlabs.exceptions import ServerError
        from endorlabs.types import ListParameters

        # Use a filter to limit scope and avoid timeout
        # Filter by CREATE operation to reduce dataset size
        list_params = ListParameters(
            filter="spec.operation==OPERATION_CREATE",
            page_size=TEST_TRAVERSE_PAGE_SIZE,
            traverse=True,
        )

        try:
            logs = self.endor_root_client.finding_log.list(
                list_params=list_params,
                max_pages=TEST_MAX_PAGES_TRAVERSE,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")

        assert isinstance(logs, list), "Should return a list of finding logs"
        print(f"Found {len(logs)} CREATE finding logs across all namespaces")

        if logs:
            # Show namespace distribution
            namespaces = {}
            for log in logs:
                ns = log.tenant_meta.namespace if log.tenant_meta else "unknown"
                namespaces[ns] = namespaces.get(ns, 0) + 1

            print(f"Finding logs found in {len(namespaces)} namespaces:")
            for ns, count in list(namespaces.items())[:5]:  # Show first 5
                print(f"  {ns}: {count} logs")

    def test_finding_log_update_raises_not_implemented(self) -> None:
        """When update_fn is None, client.finding_log.update raises NotImplemented."""
        from unittest.mock import Mock

        import endorlabs

        mock = Mock(spec=APIClient)
        client = endorlabs.Client(
            api_client=mock,
            tenant=TEST_NAMESPACE_DEFAULT,
        )
        with pytest.raises(NotImplementedError, match="does not support update"):
            client.finding_log.update("dummy-uuid", {}, update_mask="meta.description")
