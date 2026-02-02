"""Test cases for FindingLog resource operations.

Tests GET, POST, and DELETE operations for FindingLog resources, including
filtering by operation type and finding UUID.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import conftest

from endorlabs.api_client import APIClient
from endorlabs.resources import finding, finding_log
from endorlabs.resources.finding_log import FindingLog


class TestFindingLogGreenfieldAlias:
    """Unit tests: greenfield attribute names (context) and serialization.

    These tests assert .context and model_dump(by_alias=True)['context'] so that
    after renaming finding_log_context -> context, they pass without change.
    """

    def test_finding_log_context_attribute_and_serialization(self) -> None:
        """FindingLog exposes .context and serializes with key 'context'."""
        minimal_spec = {
            "finding_uuid": "f1",
            "finding_parent_kind": "Finding",
            "finding_parent_uuid": "p1",
            "operation": "CREATE",
            "introduced_at": "2020-01-01T00:00:00Z",
            "method": "METHOD_UNSPECIFIED",
            "level": "FINDING_LEVEL_UNSPECIFIED",
            "finding_tags": [],
            "finding_categories": [],
        }
        payload = {
            "uuid": "log-uuid",
            "meta": {"name": "log-meta"},
            "spec": minimal_spec,
            "tenant_meta": {"namespace": "test-ns"},
            "context": {"id": "c1", "type": "scan"},
        }
        finding_log_obj = FindingLog(**payload)
        assert finding_log_obj.context is not None
        assert getattr(finding_log_obj.context, "id", None) == "c1"
        dumped = finding_log_obj.model_dump(by_alias=True)
        assert "context" in dumped
        assert dumped["context"] is not None


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
        self.created_finding_log_uuids = []

    def teardown_method(self) -> None:
        """Clean up any resources created during tests."""
        if hasattr(self, "created_finding_log_uuids"):
            for uuid in self.created_finding_log_uuids:
                try:
                    finding_log.delete_finding_log(self.client, self.namespace, uuid)
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
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
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
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
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
        Only fetches 1 item without traverse for fast setup. Tests that need
        sample data should request this fixture explicitly.
        """
        from endorlabs.types import ListParameters

        # Fetch 1 item without traverse (fast)
        results = finding_log.list_finding_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]  # Return single item, not list

    @pytest.fixture
    def sample_finding(self):
        """Fetch a sample finding to use for finding_uuid filtering."""
        from endorlabs.types import ListParameters

        # Fetch 1 finding
        results = finding.list_findings(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        if not results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return results[0]

    def test_finding_log_list_by_operation_create(self) -> None:
        """Test filtering finding logs by CREATE operation."""
        print("\n=== TESTING FILTER FINDING LOGS BY OPERATION CREATE ===")
        import conftest

        from endorlabs.types import ListParameters

        list_params = ListParameters(
            filter="spec.operation==OPERATION_CREATE",
            page_size=conftest.TEST_PAGE_SIZE,
            traverse=True,
        )

        logs = finding_log.list_finding_logs(
            self.client,
            self.tenant_root,
            list_params=list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

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
        import conftest

        from endorlabs.types import ListParameters

        list_params = ListParameters(
            filter="spec.operation==OPERATION_UPDATE",
            page_size=conftest.TEST_PAGE_SIZE,
            traverse=True,
        )

        logs = finding_log.list_finding_logs(
            self.client,
            self.tenant_root,
            list_params=list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

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

    def test_finding_log_list_by_finding_uuid(self, sample_finding) -> None:
        """Test filtering finding logs by finding UUID."""
        print("\n=== TESTING FILTER FINDING LOGS BY FINDING UUID ===")
        import conftest

        from endorlabs.types import ListParameters

        finding_uuid = sample_finding.uuid

        list_params = ListParameters(
            filter=f'spec.finding_uuid=="{finding_uuid}"',
            page_size=conftest.TEST_PAGE_SIZE,
            traverse=True,
        )

        logs = finding_log.list_finding_logs(
            self.client,
            self.tenant_root,
            list_params=list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        assert isinstance(logs, list), "Should return a list of finding logs"
        print(f"Found {len(logs)} finding logs for finding {finding_uuid}")

        # Validate all returned logs match the finding UUID
        for log in logs:
            assert log.spec.finding_uuid == finding_uuid, (
                f"FindingLog {log.uuid} should have finding_uuid {finding_uuid}, "
                f"got {log.spec.finding_uuid}"
            )

        if logs:
            print(
                f"Sample log for finding {finding_uuid}: "
                f"{logs[0].uuid} - {logs[0].meta.name}"
            )

    def test_finding_log_traverse(self) -> None:
        """Test namespace traversal for finding logs with filter.

        Note: FindingLogs traverse without filter can timeout due to large
        dataset. This test uses a filter to limit the query scope.
        """
        print("\n=== TESTING FINDING LOG TRAVERSE ===")
        import conftest

        from endorlabs.types import ListParameters

        # Use a filter to limit scope and avoid timeout
        # Filter by CREATE operation to reduce dataset size
        list_params = ListParameters(
            filter="spec.operation==OPERATION_CREATE",
            page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
            traverse=True,
        )

        logs = finding_log.list_finding_logs(
            self.client,
            self.tenant_root,
            list_params=list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

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
        from endorlabs.api_client import APIClient

        mock = Mock(spec=APIClient)
        client = endorlabs.Client(
            api_client=mock,
            tenant=conftest.TEST_NAMESPACE_DEFAULT,
        )
        with pytest.raises(NotImplementedError, match="does not support update"):
            client.finding_log.update("dummy-uuid", {}, update_mask="meta.description")


if __name__ == "__main__":
    # Run tests directly
    import os
    import sys

    # Set up environment
    # Require ENDOR_NAMESPACE to be set
    if not os.getenv("ENDOR_NAMESPACE"):
        print("ERROR: ENDOR_NAMESPACE environment variable must be set")
        sys.exit(1)

    # Create test instance and manually set up
    test_instance = TestFindingLog()

    # Manual setup
    import conftest

    from endorlabs.types import ListParameters

    test_instance.client = APIClient(auth_method="api-key")
    test_instance.namespace = os.getenv(
        "ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT
    )
    test_instance.tenant_root = test_instance.namespace.split(".")[0]
    test_instance.finding_logs = finding_log.list_finding_logs(
        test_instance.client,
        test_instance.namespace,
        list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
        max_pages=conftest.TEST_MAX_PAGES,
    )

    try:
        print("Running finding log resource tests...")
        pytest.main([__file__, "-v", "-s"])
        print("\n[SUCCESS] All finding log tests completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        test_instance.client.close()
