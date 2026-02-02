"""Test cases for AuditLog resource operations.

Tests full CRUD operations for AuditLog resources including active and archived
logs, filtering capabilities, and API key activity identification.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pathlib import Path

from endorlabs.api_client import APIClient
from endorlabs.resources import audit_log
from endorlabs.resources.audit_log import AuditLogOperation
from endorlabs.types import ListParameters

# Add tests directory to path to import conftest
tests_dir = Path(__file__).parent
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

from datetime import UTC

import conftest


@pytest.mark.integration
@pytest.mark.long
class TestAuditLog:
    """Test cases for AuditLog resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace, root_namespace) -> None:
        """Set up test environment (client and namespace from conftest)."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.tenant_root = root_namespace
        self.created_audit_log_uuids = []

        self.audit_logs = audit_log.list_audit_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
        )

    def teardown_method(self) -> None:
        """Clean up any audit logs created during tests."""
        if hasattr(self, "created_audit_log_uuids"):
            for log_uuid in self.created_audit_log_uuids:
                try:
                    audit_log.delete_audit_log(self.client, self.namespace, log_uuid)
                    print(f"[CLEANUP] Deleted test audit log: {log_uuid}")
                except Exception as e:
                    print(f"[WARNING] Failed to delete test audit log {log_uuid}: {e}")
            self.created_audit_log_uuids.clear()

    def test_audit_log_list(self) -> None:
        """LIST from tenant root with traverse (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        result = client.audit_log.list(
            traverse=True,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        assert isinstance(result, list)

    def test_audit_log_get(self) -> None:
        """GET first item from LIST (root + traverse) (registry-based)."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.audit_log.list(
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
        got = client.audit_log.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    def test_audit_log_list_archived(self) -> None:
        """Test GET archived audit logs operation."""
        print("\n=== TESTING GET ARCHIVED AUDIT LOGS ===")

        # Test list_archived_audit_logs with pagination limits
        archived_logs = audit_log.list_archived_audit_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
            max_pages=conftest.TEST_MAX_PAGES,
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

    def test_audit_log_filter_by_operation(self) -> None:
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
                max_pages=conftest.TEST_MAX_PAGES,
            )
            print(f"{operation_type.value}: {len(filtered_logs)} logs")

            # Verify all returned logs have the correct operation type
            for log_item in filtered_logs:
                if log_item.spec:
                    assert log_item.spec.operation == operation_type, (
                        f"Log should be of operation type {operation_type}"
                    )

    def test_audit_log_filter_by_message_kind(self) -> None:
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
            max_pages=conftest.TEST_MAX_PAGES,
        )
        print(f"Message Kind '{message_kind}': {len(filtered_logs)} logs")

        # Verify all returned logs have the correct message kind
        for log_item in filtered_logs:
            if log_item.spec and log_item.spec.message_kind:
                assert log_item.spec.message_kind == message_kind, (
                    f"Log should be of message kind {message_kind}"
                )

    def test_audit_log_filter_by_time_range(self) -> None:
        """Test filtering audit logs by time range."""
        print("\n=== TESTING FILTER BY TIME RANGE ===")

        # Test filtering by recent time range (last 7 days)
        from datetime import datetime, timedelta

        to_date = datetime.now(UTC)
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
            max_pages=conftest.TEST_MAX_PAGES,
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
                    log_time = log_time.replace(tzinfo=UTC)
                assert from_date <= log_time <= to_date, (
                    "Log should be within time range"
                )

    def test_audit_log_filter_by_claims(self) -> None:
        """Test filtering audit logs by authentication claims."""
        print("\n=== TESTING FILTER BY CLAIMS ===")

        # Test filtering by claims (API key identification)
        # Note: This is a regex match, so we search for patterns
        filtered_logs = audit_log.list_audit_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(
                filter="spec.claims matches '.*api-key.*'",
                page_size=conftest.TEST_PAGE_SIZE,
            ),
            max_pages=conftest.TEST_MAX_PAGES,
        )
        print(f"Claims containing 'api-key': {len(filtered_logs)} logs")

        # Display claims from matching logs
        for log_item in filtered_logs[:3]:  # Show first 3
            if log_item.spec and log_item.spec.claims:
                print(f"  Log {log_item.uuid} claims: {log_item.spec.claims}")

    def test_audit_log_filter_by_remote_address(self) -> None:
        """Test filtering audit logs by remote address.

        Uses traverse=True to search across all namespaces for logs with
        remote_address, similar to test_audit_log_traverse pattern.
        """
        print("\n=== TESTING FILTER BY REMOTE ADDRESS ===")
        import conftest

        from endorlabs.types import ListParameters

        # Use traverse with filter to find logs with remote_address across namespaces
        # Filter to find logs that have a non-empty remote_address
        list_params = ListParameters(
            filter="spec.remote_address!=''",
            page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
            traverse=True,
        )

        logs_with_remote = audit_log.list_audit_logs(
            self.client,
            self.tenant_root,
            list_params=list_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )

        if not logs_with_remote:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

        # Get first log with remote address to use as filter target
        sample_log = logs_with_remote[0]
        if not sample_log.spec or not sample_log.spec.remote_address:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")

        remote_addr = sample_log.spec.remote_address
        print(f"Filtering by remote address: {remote_addr}")

        # Now filter by the specific remote address
        filter_params = ListParameters(
            filter=f"spec.remote_address=='{remote_addr}'",
            page_size=conftest.TEST_TRAVERSE_PAGE_SIZE,
            traverse=True,
        )

        filtered_logs = audit_log.list_audit_logs(
            self.client,
            self.tenant_root,
            list_params=filter_params,
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        print(f"Remote address '{remote_addr}': {len(filtered_logs)} logs")

        # Verify all returned logs have the correct remote address
        for log_item in filtered_logs:
            if log_item.spec and log_item.spec.remote_address:
                assert log_item.spec.remote_address == remote_addr, (
                    f"Log should have remote address {remote_addr}"
                )

    def test_audit_log_api_key_activity(self) -> None:
        """Test identifying API key activity via claims."""
        print("\n=== TESTING API KEY ACTIVITY IDENTIFICATION ===")

        # Filter for logs that might contain API key claims
        # API keys typically have claims like 'api-key' or specific patterns
        api_key_logs = audit_log.list_audit_logs(
            self.client,
            self.namespace,
            list_params=ListParameters(
                filter="spec.claims matches '.*api-key.*'",
                page_size=conftest.TEST_PAGE_SIZE,
            ),
            max_pages=conftest.TEST_MAX_PAGES,
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
                list_params=ListParameters(
                    filter=pattern, page_size=conftest.TEST_PAGE_SIZE
                ),
                max_pages=conftest.TEST_MAX_PAGES,
            )
            print(f"Pattern '{pattern}': {len(filtered_logs)} logs")

    def test_audit_log_update_raises_not_implemented(self) -> None:
        """When update_fn is None, client.audit_log.update raises NotImplemented."""
        from unittest.mock import Mock

        import endorlabs
        from endorlabs.api_client import APIClient

        mock = Mock(spec=APIClient)
        client = endorlabs.Client(
            api_client=mock,
            tenant=conftest.TEST_NAMESPACE_DEFAULT,
        )
        with pytest.raises(NotImplementedError, match="does not support update"):
            client.audit_log.update("dummy-uuid", {}, update_mask="meta.description")


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
    test_instance.namespace = os.getenv(
        "ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT
    )
    parts = test_instance.namespace.split(".", 1)
    test_instance.root_namespace = (
        parts[0] if len(parts) > 1 else test_instance.namespace
    )
    test_instance.tenant_root = test_instance.root_namespace
    test_instance.audit_logs = audit_log.list_audit_logs(
        test_instance.client,
        test_instance.namespace,
        list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
        max_pages=conftest.TEST_MAX_PAGES,
    )

    try:
        print("Running audit log resource tests...")

        # Run all tests
        test_instance.test_audit_log_list()
        test_instance.test_audit_log_get()
        test_instance.test_audit_log_list_archived()
        test_instance.test_audit_log_filter_by_operation()
        test_instance.test_audit_log_filter_by_message_kind()
        test_instance.test_audit_log_filter_by_time_range()
        test_instance.test_audit_log_filter_by_claims()
        test_instance.test_audit_log_filter_by_remote_address()
        test_instance.test_audit_log_structure_analysis()
        test_instance.test_audit_log_api_key_activity()
        test_instance.test_audit_log_schema_drift_detection()
        test_instance.test_audit_log_operations_summary()

        print("\n[SUCCESS] All audit log tests completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        test_instance.client.close()
