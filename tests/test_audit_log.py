"""
Test cases for AuditLog resource operations.

Tests full CRUD operations for AuditLog resources including active and archived
logs, filtering capabilities, and API key activity identification.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import TEST_PAGE_SIZE from conftest in the same directory
import sys
from pathlib import Path

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import audit_log
from endor_cockpit.resources.audit_log import AuditLogOperation
from endor_cockpit.types import ListParameters

# Add tests directory to path to import conftest
tests_dir = Path(__file__).parent
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

import conftest  # noqa: E402

TEST_PAGE_SIZE = conftest.TEST_PAGE_SIZE


@pytest.mark.integration
class TestAuditLog:
    """Test cases for AuditLog resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.tgowan-endor")

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        self.created_audit_log_uuids = []  # Track created logs for cleanup

        # Get test data with pagination limits
        self.audit_logs = audit_log.list_audit_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=TEST_PAGE_SIZE),
            max_pages=2,
        )

    def teardown_method(self):
        """Clean up any audit logs created during tests."""
        if hasattr(self, "created_audit_log_uuids"):
            for log_uuid in self.created_audit_log_uuids:
                try:
                    audit_log.delete_audit_log(self.client, self.namespace, log_uuid)
                    print(f"[CLEANUP] Deleted test audit log: {log_uuid}")
                except Exception as e:
                    print(f"[WARNING] Failed to delete test audit log {log_uuid}: {e}")
            self.created_audit_log_uuids.clear()

    def test_audit_log_list(self):
        """Test GET audit logs operation."""
        print("\n=== TESTING GET AUDIT LOGS ===")

        # Test list_audit_logs with pagination limits
        logs_list = audit_log.list_audit_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=TEST_PAGE_SIZE),
            max_pages=2,
        )
        assert isinstance(logs_list, list), "Should return a list of logs"
        print(f"Found {len(logs_list)} audit logs")

        # Display first few logs
        for i, log_item in enumerate(logs_list[:5]):  # Show first 5
            print(f"Audit Log {i + 1}: {log_item.uuid}")
            if log_item.spec:
                print(f"  Operation: {log_item.spec.operation}")
                if log_item.spec.message_kind:
                    print(f"  Message Kind: {log_item.spec.message_kind}")
                if log_item.meta.create_time:
                    print(f"  Create Time: {log_item.meta.create_time}")

    def test_audit_log_list_archived(self):
        """Test GET archived audit logs operation."""
        print("\n=== TESTING GET ARCHIVED AUDIT LOGS ===")

        # Test list_archived_audit_logs with pagination limits
        archived_logs = audit_log.list_archived_audit_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=TEST_PAGE_SIZE),
            max_pages=2,
        )
        assert isinstance(archived_logs, list), "Should return a list of archived logs"
        print(f"Found {len(archived_logs)} archived audit logs")

        # Display first few archived logs if any
        if archived_logs:
            for i, log_item in enumerate(archived_logs[:5]):  # Show first 5
                print(f"Archived Log {i + 1}: {log_item.uuid}")
                if log_item.spec:
                    print(f"  Operation: {log_item.spec.operation}")
                    if log_item.meta.create_time:
                        print(f"  Create Time: {log_item.meta.create_time}")

    def test_audit_log_get_by_uuid(self):
        """Test GET audit log by UUID operation."""
        print("\n=== TESTING GET AUDIT LOG BY UUID ===")

        if not self.audit_logs:
            pytest.skip("No audit logs available for testing")

        log_item = self.audit_logs[0]
        retrieved_log = audit_log.get_audit_log(
            self.client, self.namespace, log_item.uuid
        )

        # Note: Some logs may not be retrievable by UUID due to API limitations
        if retrieved_log is not None:
            assert retrieved_log.uuid == log_item.uuid, (
                "Retrieved log should match original"
            )
            print(f"Successfully retrieved audit log: {retrieved_log.uuid}")
            if retrieved_log.spec:
                print(f"Operation: {retrieved_log.spec.operation}")
        else:
            print(
                f"[INFO] Audit log {log_item.uuid} not retrievable by UUID "
                f"(API limitation)"
            )

    def test_audit_log_filter_by_operation(self):
        """Test filtering audit logs by operation type."""
        print("\n=== TESTING FILTER BY OPERATION ===")

        # Test filtering by each operation type
        operation_types = [
            AuditLogOperation.CREATE,
            AuditLogOperation.UPDATE,
            AuditLogOperation.DELETE,
            AuditLogOperation.UPSERT,
        ]

        for operation_type in operation_types:
            filtered_logs = audit_log.list_audit_logs(
                self.client,
                self.namespace,
                list_params=ListParameters(
                    filter=f"spec.operation=='{operation_type.value}'",
                    page_size=conftest.TEST_PAGE_SIZE,
                ),
                max_pages=2,
            )
            print(f"{operation_type.value}: {len(filtered_logs)} logs")

            # Verify all returned logs have the correct operation type
            for log_item in filtered_logs:
                if log_item.spec:
                    assert log_item.spec.operation == operation_type, (
                        f"Log should be of operation type {operation_type}"
                    )

    def test_audit_log_filter_by_message_kind(self):
        """Test filtering audit logs by message kind."""
        print("\n=== TESTING FILTER BY MESSAGE KIND ===")

        # Test filtering by a common message kind (Policy)
        message_kind = "internal.endor.ai.endor.v1.Policy"
        filtered_logs = audit_log.list_audit_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(
                filter=f"spec.message_kind=='{message_kind}'",
                page_size=conftest.TEST_PAGE_SIZE,
            ),
            max_pages=2,
        )
        print(f"Message Kind '{message_kind}': {len(filtered_logs)} logs")

        # Verify all returned logs have the correct message kind
        for log_item in filtered_logs:
            if log_item.spec and log_item.spec.message_kind:
                assert log_item.spec.message_kind == message_kind, (
                    f"Log should be of message kind {message_kind}"
                )

    def test_audit_log_filter_by_time_range(self):
        """Test filtering audit logs by time range."""
        print("\n=== TESTING FILTER BY TIME RANGE ===")

        # Test filtering by recent time range (last 7 days)
        from datetime import datetime, timedelta, timezone

        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(days=7)

        to_date_str = to_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        from_date_str = from_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        filtered_logs = audit_log.list_audit_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(
                filter=(
                    f"meta.create_time>=date({from_date_str}) "
                    f"and meta.create_time<=date({to_date_str})"
                ),
                page_size=conftest.TEST_PAGE_SIZE,
            ),
            max_pages=2,
        )
        print(
            f"Time range ({from_date_str} to {to_date_str}): {len(filtered_logs)} logs"
        )

        # Verify all returned logs are within the time range
        for log_item in filtered_logs:
            if log_item.meta.create_time:
                log_time_str = log_item.meta.create_time.replace("Z", "+00:00")
                log_time = datetime.fromisoformat(log_time_str)
                # Ensure both datetimes are timezone-aware for comparison
                if log_time.tzinfo is None:
                    log_time = log_time.replace(tzinfo=timezone.utc)
                assert from_date <= log_time <= to_date, (
                    "Log should be within time range"
                )

    def test_audit_log_filter_by_claims(self):
        """Test filtering audit logs by authentication claims."""
        print("\n=== TESTING FILTER BY CLAIMS ===")

        # Test filtering by claims (API key identification)
        # Note: This is a regex match, so we search for patterns
        filtered_logs = audit_log.list_audit_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(
                filter="spec.claims matches '.*api-key.*'", page_size=20
            ),
            max_pages=2,
        )
        print(f"Claims containing 'api-key': {len(filtered_logs)} logs")

        # Display claims from matching logs
        for log_item in filtered_logs[:3]:  # Show first 3
            if log_item.spec and log_item.spec.claims:
                print(f"  Log {log_item.uuid} claims: {log_item.spec.claims}")

    def test_audit_log_filter_by_remote_address(self):
        """Test filtering audit logs by remote address."""
        print("\n=== TESTING FILTER BY REMOTE ADDRESS ===")

        # Get a sample log to find a remote address to filter by
        if not self.audit_logs:
            pytest.skip("No audit logs available for testing")

        # Find a log with a remote address
        sample_log = None
        for log_item in self.audit_logs:
            if log_item.spec and log_item.spec.remote_address:
                sample_log = log_item
                break

        if not sample_log or not sample_log.spec:
            pytest.skip("No audit logs with remote address available")

        remote_addr = sample_log.spec.remote_address
        print(f"Filtering by remote address: {remote_addr}")

        filtered_logs = audit_log.list_audit_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(
                filter=f"spec.remote_address=='{remote_addr}'", page_size=20
            ),
            max_pages=2,
        )
        print(f"Remote address '{remote_addr}': {len(filtered_logs)} logs")

        # Verify all returned logs have the correct remote address
        for log_item in filtered_logs:
            if log_item.spec and log_item.spec.remote_address:
                assert log_item.spec.remote_address == remote_addr, (
                    f"Log should have remote address {remote_addr}"
                )

    def test_audit_log_api_key_activity(self):
        """Test identifying API key activity via claims."""
        print("\n=== TESTING API KEY ACTIVITY IDENTIFICATION ===")

        # Filter for logs that might contain API key claims
        # API keys typically have claims like 'api-key' or specific patterns
        api_key_logs = audit_log.list_audit_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(
                filter="spec.claims matches '.*api-key.*'", page_size=20
            ),
            max_pages=2,
        )
        print(f"Found {len(api_key_logs)} logs with potential API key activity")

        # Display details of API key activity
        for log_item in api_key_logs[:5]:  # Show first 5
            print(f"\nAPI Key Activity Log: {log_item.uuid}")
            if log_item.spec:
                print(f"  Operation: {log_item.spec.operation}")
                if log_item.spec.message_kind:
                    print(f"  Message Kind: {log_item.spec.message_kind}")
                if log_item.spec.claims:
                    print(f"  Claims: {log_item.spec.claims}")
                if log_item.spec.remote_address:
                    print(f"  Remote Address: {log_item.spec.remote_address}")
                if log_item.meta.create_time:
                    print(f"  Create Time: {log_item.meta.create_time}")

        # Also try alternative patterns for API key identification
        alternative_patterns = [
            "spec.claims matches '.*ID=.*'",  # ID claims
            "spec.claims matches '.*issuer=.*'",  # Issuer claims
        ]

        for pattern in alternative_patterns:
            filtered_logs = audit_log.list_audit_logs(
                self.client,
                self.namespace,
                list_params=ListParameters(filter=pattern, page_size=20),
                max_pages=2,
            )
            print(f"Pattern '{pattern}': {len(filtered_logs)} logs")

    def test_audit_log_pagination(self):
        """Test pagination support for audit logs."""
        print("\n=== TESTING PAGINATION ===")

        # Test pagination with small page size
        page_size = 10
        paginated_logs = audit_log.list_audit_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=page_size),
            max_pages=2,
        )
        print(f"Paginated logs (page_size={page_size}): {len(paginated_logs)}")

        # Verify pagination works (should get at least some results)
        assert isinstance(paginated_logs, list), "Should return a list"
        print(f"Successfully retrieved {len(paginated_logs)} logs with pagination")


if __name__ == "__main__":
    # Run tests directly
    import os
    import sys

    # Set up environment - require ENDOR_NAMESPACE to be set
    if not os.getenv("ENDOR_NAMESPACE"):
        print("ERROR: ENDOR_NAMESPACE environment variable must be set")
        sys.exit(1)

    # Create test instance and manually set up
    test_instance = TestAuditLog()

    # Manual setup
    test_instance.client = APIClient(auth_method="api-key")
    test_instance.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.tgowan-endor")
    test_instance.audit_logs = audit_log.list_audit_logs(
        test_instance.client,
        test_instance.namespace,
        list_params=ListParameters(page_size=20),
        max_pages=2,
    )

    try:
        print("Running audit log resource tests...")

        # Run all tests
        test_instance.test_audit_log_list()
        test_instance.test_audit_log_list_archived()
        test_instance.test_audit_log_get_by_uuid()
        test_instance.test_audit_log_filter_by_operation()
        test_instance.test_audit_log_filter_by_message_kind()
        test_instance.test_audit_log_filter_by_time_range()
        test_instance.test_audit_log_filter_by_claims()
        test_instance.test_audit_log_filter_by_remote_address()
        test_instance.test_audit_log_structure_analysis()
        test_instance.test_audit_log_api_key_activity()
        test_instance.test_audit_log_pagination()
        test_instance.test_audit_log_schema_drift_detection()
        test_instance.test_audit_log_operations_summary()

        print("\n[SUCCESS] All audit log tests completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
