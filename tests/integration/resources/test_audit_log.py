"""Test cases for AuditLog resource operations.

Tests full CRUD operations for AuditLog resources including active and archived
logs, filtering capabilities, and API key activity identification.
"""

from datetime import UTC

import pytest

import endorlabs
from endorlabs.api_client import APIClient
from endorlabs.core.types import ListParameters
from endorlabs.resources.audit_log import AuditLogOperation
from tests.conftest import (
    TEST_MAX_PAGES,
    TEST_MAX_PAGES_TRAVERSE,
    TEST_NAMESPACE_DEFAULT,
    TEST_PAGE_SIZE,
    TEST_TRAVERSE_PAGE_SIZE,
)


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
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.endor_root_client = endorlabs.Client(
            tenant=root_namespace, api_client=api_client
        )

        self.audit_logs = self.endor_client.audit_log.list(
            list_params=ListParameters(page_size=TEST_PAGE_SIZE),
            max_pages=TEST_MAX_PAGES,
        )

    def teardown_method(self) -> None:
        """Clean up any audit logs created during tests."""
        if hasattr(self, "created_audit_log_uuids"):
            for log_uuid in self.created_audit_log_uuids:
                try:
                    self.endor_client.audit_log.delete(log_uuid)
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
            max_pages=TEST_MAX_PAGES_TRAVERSE,
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
        got = client.audit_log.get(item.uuid, namespace=ns)
        assert got is not None
        assert got.uuid == item.uuid

    def test_audit_log_spec_error_has_code_message_details(self) -> None:
        """AuditLog spec.error exposes code, message, details when present."""
        import endorlabs

        client = endorlabs.Client(
            tenant=self.root_namespace,
            api_client=self.client,
        )
        items = client.audit_log.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        if item.spec is not None:
            assert hasattr(item.spec, "error")
            if item.spec.error is not None:
                assert hasattr(item.spec.error, "code")
                assert hasattr(item.spec.error, "message")
                assert hasattr(item.spec.error, "details")
        ns = (
            item.tenant_meta.namespace
            if item.tenant_meta and getattr(item.tenant_meta, "namespace", None)
            else self.root_namespace
        )
        got = client.audit_log.get(item.uuid, namespace=ns)
        if got and got.spec and got.spec.error is not None:
            assert hasattr(got.spec.error, "code")
            assert hasattr(got.spec.error, "message")
            assert hasattr(got.spec.error, "details")

    def test_audit_log_list_archived(self) -> None:
        """Test listing archived audit logs via archive=True.

        Archived logs are 30+ days old and retained for up to 3 years.
        Active and archived logs must be queried separately.
        """
        print("\n=== TESTING LIST ARCHIVED AUDIT LOGS ===")

        archived = self.endor_client.audit_log.list(
            archive=True,
            page_size=TEST_PAGE_SIZE,
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(archived, list), "Should return a list"

        if not archived:
            pytest.skip("No archived audit logs in this tenant (< 30 days old)")

        print(f"Found {len(archived)} archived audit logs")

        # Verify returned logs have expected structure
        for log in archived:
            assert log.uuid, "Archived log should have a UUID"
            assert log.meta, "Archived log should have metadata"

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
            filtered_logs = self.endor_client.audit_log.list(
                list_params=ListParameters(
                    filter=f"spec.operation=='{operation_type.value}'",
                    page_size=TEST_PAGE_SIZE,
                ),
                max_pages=TEST_MAX_PAGES,
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
        filtered_logs = self.endor_client.audit_log.list(
            list_params=ListParameters(
                filter=f"spec.message_kind=='{message_kind}'",
                page_size=TEST_PAGE_SIZE,
            ),
            max_pages=TEST_MAX_PAGES,
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

        filtered_logs = self.endor_client.audit_log.list(
            list_params=ListParameters(
                filter=(
                    f"meta.create_time>=date({from_date_str}) "
                    f"and meta.create_time<=date({to_date_str})"
                ),
                page_size=TEST_PAGE_SIZE,
            ),
            max_pages=TEST_MAX_PAGES,
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
        filtered_logs = self.endor_client.audit_log.list(
            list_params=ListParameters(
                filter="spec.claims matches '.*api-key.*'",
                page_size=TEST_PAGE_SIZE,
            ),
            max_pages=TEST_MAX_PAGES,
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
        from endorlabs.core.types import ListParameters

        # Use traverse with filter to find logs with remote_address across namespaces
        # Filter to find logs that have a non-empty remote_address
        list_params = ListParameters(
            filter="spec.remote_address!=''",
            page_size=TEST_TRAVERSE_PAGE_SIZE,
            traverse=True,
        )

        logs_with_remote = self.endor_root_client.audit_log.list(
            list_params=list_params,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
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
            page_size=TEST_TRAVERSE_PAGE_SIZE,
            traverse=True,
        )

        filtered_logs = self.endor_root_client.audit_log.list(
            list_params=filter_params,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
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
        api_key_logs = self.endor_client.audit_log.list(
            list_params=ListParameters(
                filter="spec.claims matches '.*api-key.*'",
                page_size=TEST_PAGE_SIZE,
            ),
            max_pages=TEST_MAX_PAGES,
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
            filtered_logs = self.endor_client.audit_log.list(
                list_params=ListParameters(filter=pattern, page_size=TEST_PAGE_SIZE),
                max_pages=TEST_MAX_PAGES,
            )
            print(f"Pattern '{pattern}': {len(filtered_logs)} logs")

    def test_audit_log_update_raises_not_implemented(self) -> None:
        """When update_fn is None, client.audit_log.update raises NotImplemented."""
        from unittest.mock import Mock

        import endorlabs

        mock = Mock(spec=APIClient)
        client = endorlabs.Client(
            api_client=mock,
            tenant=TEST_NAMESPACE_DEFAULT,
        )
        with pytest.raises(NotImplementedError, match="does not support update"):
            client.audit_log.update("dummy-uuid", {}, update_mask="meta.description")
