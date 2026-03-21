"""Test cases for ScanLogRequest resource operations.

Tests the request-based API for retrieving scan result logs. ScanLogRequest
is a special case - it's not standard CRUD, but a request-based API that
returns logs in the response.
"""

import pytest

import endorlabs
from endorlabs.core.types import ListParameters
from endorlabs.resources import scan_log_request
from endorlabs.resources.scan_log_request import (
    CreateScanLogRequestPayload,
    ScanLogLevel,
    ScanLogRequestMetaCreate,
    ScanLogRequestSpecCreate,
)
from tests.conftest import (
    TEST_MAX_PAGES,
    TEST_MAX_PAGES_TRAVERSE,
    TEST_PAGE_SIZE,
    TEST_TRAVERSE_PAGE_SIZE,
)


@pytest.mark.integration
@pytest.mark.long
class TestScanLogRequest:
    """Test cases for ScanLogRequest resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace) -> None:
        """Fast setup: client and namespace from conftest."""
        self.client = api_client
        self.namespace = namespace
        parts = namespace.split(".")
        self.parent_namespace = parts[0] if len(parts) > 1 else namespace
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.endor_parent_client = endorlabs.Client(
            tenant=self.parent_namespace, api_client=api_client
        )

    @pytest.fixture
    def sample_scan_result(self):
        """Fetch minimal sample scan result for testing.

        Function-scoped but only fetches when explicitly requested by tests.
        Uses traverse=True to search across namespaces for scan results.
        Use .uuid and .tenant_meta.namespace so create uses the scan result's
        namespace (API requires create in same namespace as the scan result).
        """
        scan_results = self.endor_parent_client.ScanResult.list(
            list_params=ListParameters(
                page_size=TEST_TRAVERSE_PAGE_SIZE,
                traverse=True,
                sort_by="meta.create_time",
                desc=True,
            ),
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not scan_results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return scan_results[0]

    @pytest.fixture
    def sample_scan_result_uuid(self, sample_scan_result):
        """UUID of the sample scan result (for tests that only need the UUID)."""
        return sample_scan_result.uuid

    def _namespace_for_scan_result(self, sample_scan_result):
        """Namespace to use for scan-log-request create/get (same as scan result)."""
        if sample_scan_result.tenant_meta and sample_scan_result.tenant_meta.namespace:
            return sample_scan_result.tenant_meta.namespace
        return self.parent_namespace

    @pytest.mark.writes
    def test_create_scan_log_request(self, sample_scan_result) -> None:
        """Test creating a scan log request.

        Local-only: scan log request creation requires elevated permissions (403 in CI).
        """
        print("\n=== TESTING CREATE SCAN LOG REQUEST ===")
        ns = self._namespace_for_scan_result(sample_scan_result)

        # Create a log request for a scan result (use scan result's namespace)
        payload = CreateScanLogRequestPayload(
            meta=ScanLogRequestMetaCreate(name="test-scan-log-request"),
            spec=ScanLogRequestSpecCreate(
                max_entries=10,
                scan_result_uuid=sample_scan_result.uuid,
            ),
        )

        ns_client = endorlabs.Client(tenant=ns, api_client=self.client)
        request = ns_client.ScanLogRequest.create(payload)

        assert request is not None, "Should successfully create log request"
        assert request.spec is not None, "Request should have spec"
        assert request.spec.max_entries == 10, "Max entries should match"

        print(f"Created log request: {request.uuid}")
        if request.spec.log_messages:
            print(f"Retrieved {len(request.spec.log_messages)} log messages")

    def test_get_scan_result_logs_helper(self, sample_scan_result) -> None:
        """Test the convenience helper function."""
        print("\n=== TESTING GET SCAN RESULT LOGS HELPER ===")
        ns = self._namespace_for_scan_result(sample_scan_result)

        # Use the convenience helper (use scan result's namespace)
        logs = scan_log_request.get_scan_result_logs(
            self.client,
            ns,
            sample_scan_result.uuid,
            max_entries=10,
        )

        # Logs may be None or empty list depending on scan result
        if logs is not None:
            print(f"Retrieved {len(logs)} log messages")
            for log in logs[:3]:  # Show first 3
                if log.timestamp and log.level:
                    print(f"  {log.timestamp} [{log.level}]")

    @pytest.mark.writes
    def test_scan_log_request_with_filters(self, sample_scan_result) -> None:
        """Test creating log request with various filters.

        Local-only: scan log request creation requires elevated permissions (403 in CI).
        """
        print("\n=== TESTING SCAN LOG REQUEST WITH FILTERS ===")
        ns = self._namespace_for_scan_result(sample_scan_result)

        # Test with log level filter (use scan result's namespace)
        payload = CreateScanLogRequestPayload(
            meta=ScanLogRequestMetaCreate(name="test-filtered-log-request"),
            spec=ScanLogRequestSpecCreate(
                max_entries=20,
                scan_result_uuid=sample_scan_result.uuid,
                log_levels=[ScanLogLevel.ERROR, ScanLogLevel.WARNING],
                newest_first=True,
            ),
        )

        ns_client = endorlabs.Client(tenant=ns, api_client=self.client)
        request = ns_client.ScanLogRequest.create(payload)

        assert request is not None, "Should successfully create log request"
        assert request.spec.log_levels == [
            ScanLogLevel.ERROR,
            ScanLogLevel.WARNING,
        ], "Log levels should match"

        print(f"Created filtered log request: {request.uuid}")

    @pytest.mark.writes
    def test_scan_log_request_error_handling(self) -> None:
        """Test error handling for invalid scan result UUID.

        Local-only: calls create endpoint (403 with read-only CI credentials).
        """
        print("\n=== TESTING ERROR HANDLING ===")

        # Test with invalid scan result UUID format - should raise ValidationError
        # (server returns HTTP 400 with gRPC code 3 INVALID_ARGUMENT)
        from endorlabs.core.exceptions import ValidationError

        payload = CreateScanLogRequestPayload(
            meta=ScanLogRequestMetaCreate(name="test-invalid-uuid-request"),
            spec=ScanLogRequestSpecCreate(
                max_entries=10,
                scan_result_uuid="invalid-uuid",
            ),
        )

        with pytest.raises(ValidationError) as exc_info:
            self.endor_parent_client.ScanLogRequest.create(payload)
        assert exc_info.value.status_code == 400
        assert (
            "invalid" in exc_info.value.message.lower()
            or "uuid" in exc_info.value.message.lower()
        )

    def test_scan_log_level_enum(self) -> None:
        """Test ScanLogLevel enum values."""
        print("\n=== TESTING SCAN LOG LEVEL ENUM ===")

        # Test enum values
        assert ScanLogLevel.ERROR == "LOG_LEVEL_ERROR"
        assert ScanLogLevel.WARNING == "LOG_LEVEL_WARNING"
        assert ScanLogLevel.INFO == "LOG_LEVEL_INFO"
        assert ScanLogLevel.DEBUG == "LOG_LEVEL_DEBUG"

        print("All log level enum values validated")

    @pytest.mark.writes
    def test_scan_log_request_per_namespace_debug(self) -> None:
        """Per-namespace debug: list namespaces, then list scan results and try create.

        Temporary/debug test to minimize scope and see which namespace works or fails.
        Run: pytest tests/test_scan_log_request.py -v -s --log-cli-level=DEBUG
        -k per_namespace_debug
        """
        import logging

        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        print("\n=== PER-NAMESPACE SCAN LOG REQUEST DEBUG ===")

        # List namespaces under parent (traverse to get children)
        namespaces_list = self.endor_parent_client.Namespace.list(
            traverse=True,
            list_params=ListParameters(page_size=TEST_TRAVERSE_PAGE_SIZE),
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
        if not namespaces_list:
            pytest.skip("No namespaces under parent (empty list)")
        # Collect canonical namespace names (parent + children)
        ns_names = set()
        for ns_obj in namespaces_list:
            if ns_obj.tenant_meta and ns_obj.tenant_meta.namespace:
                ns_names.add(ns_obj.tenant_meta.namespace)
        if not ns_names:
            pytest.skip("No namespace paths in list response")
        print(f"Namespaces to try: {sorted(ns_names)}")

        for ns_canonical in sorted(ns_names):
            list_ok = False
            create_ok = False
            scan_result_uuid = None
            try:
                ns_client = endorlabs.Client(
                    tenant=ns_canonical, api_client=self.client
                )
                results = ns_client.ScanResult.list(
                    list_params=ListParameters(page_size=TEST_PAGE_SIZE),
                    max_pages=TEST_MAX_PAGES,
                )
                list_ok = True
                if not results:
                    print(f"  [{ns_canonical}] list_scan_results: ok, 0 results")
                    continue
                scan_result_uuid = results[0].uuid
                payload = CreateScanLogRequestPayload(
                    meta=ScanLogRequestMetaCreate(name="debug-per-ns-log-request"),
                    spec=ScanLogRequestSpecCreate(
                        max_entries=10,
                        scan_result_uuid=scan_result_uuid,
                    ),
                )
                ns_client.ScanLogRequest.create(payload)
                create_ok = True
                msg = (
                    f"  [{ns_canonical}] list_scan_results: ok, "
                    f"create_scan_log_request: ok (scan_result_uuid={scan_result_uuid})"
                )
                print(msg)
            except Exception as e:
                list_msg = "ok" if list_ok else "fail"
                create_msg = "ok" if create_ok else f"fail: {type(e).__name__}: {e!s}"
                print(
                    f"  [{ns_canonical}] list_scan_results: {list_msg}, "
                    f"create_scan_log_request: {create_msg}"
                )
                if scan_result_uuid:
                    print(f"    scan_result_uuid={scan_result_uuid}")

        # Test does not assert so it always "passes" — it is for triage/debug only
        print("=== PER-NAMESPACE DEBUG DONE ===")
