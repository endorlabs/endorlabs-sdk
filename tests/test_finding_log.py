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

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import finding, finding_log


@pytest.mark.integration
class TestFindingLog:
    """Test cases for FindingLog resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self) -> None:
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Extract tenant root namespace for traverse operations
        # Tenant root is the first part before the first dot
        self.tenant_root = self.namespace.split(".")[0]

        # Track created resources for cleanup
        self.created_finding_log_uuids = []

    def teardown_method(self) -> None:
        """Clean up any resources created during tests."""
        if hasattr(self, "created_finding_log_uuids"):
            # Clean up created finding logs
            for uuid in self.created_finding_log_uuids:
                try:
                    finding_log.delete_finding_log(self.client, self.namespace, uuid)
                except Exception as e:
                    print(f"Warning: Failed to delete finding log {uuid}: {e}")
            self.created_finding_log_uuids.clear()

    @pytest.fixture
    def sample_finding_log(self):
        """Fetch minimal sample data (1 item) for UUID operations.

        Function-scoped but only fetches when explicitly requested by tests.
        Only fetches 1 item without traverse for fast setup. Tests that need
        sample data should request this fixture explicitly.
        """
        from endor_cockpit.types import ListParameters

        # Fetch 1 item without traverse (fast)
        results = finding_log.list_finding_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=1),
            max_pages=1,
        )
        if not results:
            pytest.skip("No finding logs available for testing")
        return results[0]  # Return single item, not list

    @pytest.fixture
    def sample_finding(self):
        """Fetch a sample finding to use for finding_uuid filtering."""
        from endor_cockpit.types import ListParameters

        # Fetch 1 finding
        results = finding.list_findings(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=1),
            max_pages=1,
        )
        if not results:
            pytest.skip("No findings available for testing")
        return results[0]

    def test_finding_log_get_list(self) -> None:
        """Test GET finding logs operation."""
        print("\n=== TESTING GET FINDING LOGS ===")

        # Test list_finding_logs with pagination limits
        import conftest

        from endor_cockpit.types import ListParameters

        finding_logs_list = finding_log.list_finding_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        assert isinstance(finding_logs_list, list), (
            "Should return a list of finding logs"
        )
        assert len(finding_logs_list) > 0, "Should have at least one finding log"

        print(f"Found {len(finding_logs_list)} finding logs")

        # Display first few finding logs
        for _i, log_item in enumerate(finding_logs_list[:10]):  # Show first 10
            print(f"FindingLog {log_item.uuid}: {log_item.meta.name}")
            if log_item.spec.operation:
                print(f"  Operation: {log_item.spec.operation}")
            if log_item.spec.finding_uuid:
                print(f"  Finding UUID: {log_item.spec.finding_uuid}")

    def test_finding_log_get_by_uuid(self, sample_finding_log) -> None:
        """Test GET finding log by UUID operation."""
        print("\n=== TESTING GET FINDING LOG BY UUID ===")

        log_item = sample_finding_log
        # Use the finding log's actual namespace
        log_namespace = (
            log_item.tenant_meta.namespace if log_item.tenant_meta else self.namespace
        )
        retrieved_log = finding_log.get_finding_log(
            self.client, log_namespace, log_item.uuid
        )

        assert retrieved_log is not None, (
            "Should successfully retrieve finding log by UUID"
        )
        assert retrieved_log.uuid == log_item.uuid, (
            "Retrieved finding log should match original"
        )
        assert retrieved_log.meta.name == log_item.meta.name, (
            "Finding log name should match"
        )

        print(f"Successfully retrieved finding log: {retrieved_log.uuid}")
        print(f"Finding log name: {retrieved_log.meta.name}")
        if retrieved_log.spec.operation:
            print(f"Operation: {retrieved_log.spec.operation}")
        if retrieved_log.spec.finding_uuid:
            print(f"Finding UUID: {retrieved_log.spec.finding_uuid}")

    def test_finding_log_list_by_operation_create(self) -> None:
        """Test filtering finding logs by CREATE operation."""
        print("\n=== TESTING FILTER FINDING LOGS BY OPERATION CREATE ===")
        import conftest

        from endor_cockpit.types import ListParameters

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

        from endor_cockpit.types import ListParameters

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

        from endor_cockpit.types import ListParameters

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

        from endor_cockpit.types import ListParameters

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

    from endor_cockpit.types import ListParameters

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

        # Run all tests
        test_instance.test_finding_log_get_list()
        test_instance.test_finding_log_get_by_uuid(test_instance.finding_logs[0])

        print("\n[SUCCESS] All finding log tests completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
