"""Test cases for AuditLog resource operations.

Tests full CRUD operations for AuditLog resources including active and archived
logs, filtering capabilities, and API key activity identification.
"""

from datetime import UTC, datetime, timedelta

import pytest

import endorlabs
from endorlabs.resources.audit_log import AuditLogOperation
from tests.conftest import (
    TEST_LOG_LIST_MAX_PAGES,
    TEST_LOG_LIST_MAX_ROWS,
)
from tests.integration.conftest import (
    assert_bounded_log_rows,
    bounded_log_list_params,
    log_list_kwargs,
)


@pytest.mark.integration
class TestAuditLog:
    """Test cases for AuditLog resource operations."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace, root_namespace) -> None:
        """Set up test environment (client and namespace from conftest)."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.created_audit_log_uuids: list[str] = []
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)

        self.audit_logs = self.endor_client.AuditLog.list(
            list_params=bounded_log_list_params(),
            max_pages=TEST_LOG_LIST_MAX_PAGES,
        )
        assert_bounded_log_rows(self.audit_logs)

    def teardown_method(self) -> None:
        """Clean up any audit logs created during tests."""
        for log_uuid in self.created_audit_log_uuids:
            try:
                self.endor_client.AuditLog.delete(log_uuid)
            except Exception as e:
                print(f"[WARNING] Failed to delete test audit log {log_uuid}: {e}")
        self.created_audit_log_uuids.clear()

    def test_audit_log_list(self) -> None:
        """LIST in namespace with bounded pagination (no traverse)."""
        result = self.endor_client.AuditLog.list(**log_list_kwargs())
        assert isinstance(result, list)
        assert_bounded_log_rows(result)

    def test_audit_log_get(self) -> None:
        """GET first item from bounded LIST in namespace."""
        items = self.endor_client.AuditLog.list(**log_list_kwargs())
        assert_bounded_log_rows(items)
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        got = self.endor_client.AuditLog.get(items[0])
        assert got is not None
        assert got.uuid == items[0].uuid

    def test_audit_log_spec_error_has_code_message_details(self) -> None:
        """AuditLog spec.error exposes code, message, details when present."""
        items = self.endor_client.AuditLog.list(**log_list_kwargs())
        assert_bounded_log_rows(items)
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        item = items[0]
        if item.spec is not None:
            assert hasattr(item.spec, "error")
            if item.spec.error is not None:
                assert hasattr(item.spec.error, "code")
                assert hasattr(item.spec.error, "message")
                assert hasattr(item.spec.error, "details")
        got = self.endor_client.AuditLog.get(item)
        if got and got.spec and got.spec.error is not None:
            assert hasattr(got.spec.error, "code")
            assert hasattr(got.spec.error, "message")
            assert hasattr(got.spec.error, "details")

    def test_audit_log_list_archived(self) -> None:
        """List archived audit logs via archive=True (bounded)."""
        archived = self.endor_client.AuditLog.list(
            archive=True,
            **log_list_kwargs(),
        )
        assert isinstance(archived, list)
        assert_bounded_log_rows(archived)
        if not archived:
            pytest.skip("No archived audit logs in this tenant (< 30 days old)")
        for log in archived:
            assert log.uuid, "Archived log should have a UUID"
            assert log.meta, "Archived log should have metadata"

    def test_audit_log_filter_by_operation(self) -> None:
        """Filter audit logs by operation type (bounded per operation)."""
        for operation_type in (
            AuditLogOperation.CREATE,
            AuditLogOperation.UPDATE,
            AuditLogOperation.DELETE,
            AuditLogOperation.UPSERT,
        ):
            filtered_logs = self.endor_client.AuditLog.list(
                list_params=bounded_log_list_params(
                    filter_expr=f"spec.operation=='{operation_type.value}'",
                ),
                max_pages=TEST_LOG_LIST_MAX_PAGES,
            )
            assert_bounded_log_rows(filtered_logs)
            for log_item in filtered_logs:
                if log_item.spec:
                    assert log_item.spec.operation == operation_type

    def test_audit_log_filter_by_message_kind(self) -> None:
        """Filter audit logs by message kind (bounded)."""
        message_kind = "internal.endor.ai.endor.v1.Policy"
        filtered_logs = self.endor_client.AuditLog.list(
            list_params=bounded_log_list_params(
                filter_expr=f"spec.message_kind=='{message_kind}'",
            ),
            max_pages=TEST_LOG_LIST_MAX_PAGES,
        )
        assert_bounded_log_rows(filtered_logs)
        for log_item in filtered_logs:
            if log_item.spec and log_item.spec.message_kind:
                assert log_item.spec.message_kind == message_kind

    def test_audit_log_filter_by_time_range(self) -> None:
        """Filter audit logs by time range (bounded)."""
        to_date = datetime.now(UTC)
        from_date = to_date - timedelta(days=7)
        to_date_str = to_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        from_date_str = from_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        filtered_logs = self.endor_client.AuditLog.list(
            list_params=bounded_log_list_params(
                filter_expr=(
                    f"meta.create_time>=date({from_date_str}) "
                    f"and meta.create_time<=date({to_date_str})"
                ),
            ),
            max_pages=TEST_LOG_LIST_MAX_PAGES,
        )
        assert_bounded_log_rows(filtered_logs)
        for log_item in filtered_logs:
            if log_item.meta.create_time:
                create_time = log_item.meta.create_time
                if isinstance(create_time, datetime):
                    log_time = create_time
                else:
                    log_time_str = create_time.replace("Z", "+00:00")
                    log_time = datetime.fromisoformat(log_time_str)
                if log_time.tzinfo is None:
                    log_time = log_time.replace(tzinfo=UTC)
                assert from_date <= log_time <= to_date

    def test_audit_log_filter_by_claims(self) -> None:
        """Filter audit logs by authentication claims (bounded)."""
        filtered_logs = self.endor_client.AuditLog.list(
            list_params=bounded_log_list_params(
                filter_expr="spec.claims matches '.*api-key.*'",
            ),
            max_pages=TEST_LOG_LIST_MAX_PAGES,
        )
        assert_bounded_log_rows(filtered_logs)
        for log_item in filtered_logs[:TEST_LOG_LIST_MAX_ROWS]:
            if log_item.spec and log_item.spec.claims:
                assert any("api-key" in claim.lower() for claim in log_item.spec.claims)

    def test_audit_log_filter_by_remote_address(self) -> None:
        """Filter audit logs by remote address in namespace (bounded, no traverse)."""
        logs_with_remote = self.endor_client.AuditLog.list(
            list_params=bounded_log_list_params(
                filter_expr="spec.remote_address!=''",
            ),
            max_pages=TEST_LOG_LIST_MAX_PAGES,
        )
        assert_bounded_log_rows(logs_with_remote)
        if not logs_with_remote:
            pytest.skip("No audit logs with remote_address in namespace scope")
        sample_log = logs_with_remote[0]
        if not sample_log.spec or not sample_log.spec.remote_address:
            pytest.skip("No audit logs with remote_address in namespace scope")
        remote_addr = sample_log.spec.remote_address

        filtered_logs = self.endor_client.AuditLog.list(
            list_params=bounded_log_list_params(
                filter_expr=f"spec.remote_address=='{remote_addr}'",
            ),
            max_pages=TEST_LOG_LIST_MAX_PAGES,
        )
        assert_bounded_log_rows(filtered_logs)
        for log_item in filtered_logs:
            if log_item.spec and log_item.spec.remote_address:
                assert log_item.spec.remote_address == remote_addr

    def test_audit_log_api_key_activity(self) -> None:
        """Identify API key activity via claims (bounded)."""
        api_key_logs = self.endor_client.AuditLog.list(
            list_params=bounded_log_list_params(
                filter_expr="spec.claims matches '.*api-key.*'",
            ),
            max_pages=TEST_LOG_LIST_MAX_PAGES,
        )
        assert_bounded_log_rows(api_key_logs)
        for log_item in api_key_logs[:TEST_LOG_LIST_MAX_ROWS]:
            if log_item.spec and log_item.spec.claims:
                assert any("api-key" in claim.lower() for claim in log_item.spec.claims)

        for pattern in (
            "spec.claims matches '.*ID=.*'",
            "spec.claims matches '.*issuer=.*'",
        ):
            filtered_logs = self.endor_client.AuditLog.list(
                list_params=bounded_log_list_params(filter_expr=pattern),
                max_pages=TEST_LOG_LIST_MAX_PAGES,
            )
            assert_bounded_log_rows(filtered_logs)
