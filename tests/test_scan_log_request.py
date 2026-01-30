"""Test cases for ScanLogRequest resource operations.

Tests the request-based API for retrieving scan result logs. ScanLogRequest
is a special case - it's not standard CRUD, but a request-based API that
returns logs in the response.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import conftest

from endorlabs.api_client import APIClient
from endorlabs.resources import scan_log_request, scan_result
from endorlabs.resources.scan_log_request import (
    CreateScanLogRequestPayload,
    ScanLogLevel,
    ScanLogRequestMetaCreate,
    ScanLogRequestSpecCreate,
)
from endorlabs.types import ListParameters


@pytest.mark.integration
class TestScanLogRequest:
    """Test cases for ScanLogRequest resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self) -> None:
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT)

        # Validate namespace is set
        if not self.namespace:
            pytest.skip("ENDOR_NAMESPACE environment variable must be set")

        # Get test data - use parent namespace to access child resources
        parts = self.namespace.split(".")
        self.parent_namespace = parts[0] if len(parts) > 1 else self.namespace

    @pytest.fixture
    def sample_scan_result_uuid(self):
        """Fetch minimal sample scan result UUID for testing.

        Function-scoped but only fetches when explicitly requested by tests.
        Uses traverse=True to search across namespaces for scan results.
        """
        # Get a scan result to test log retrieval
        scan_results = scan_result.list_scan_results(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=1, traverse=True),
            max_pages=conftest.TEST_MAX_PAGES_TRAVERSE,
        )
        if not scan_results:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        return scan_results[0].uuid

    @pytest.mark.writes
    def test_create_scan_log_request(self, sample_scan_result_uuid) -> None:
        """Test creating a scan log request.

        Local-only: scan log request creation requires elevated permissions (403 in CI).
        """
        print("\n=== TESTING CREATE SCAN LOG REQUEST ===")

        # Create a log request for a scan result
        payload = CreateScanLogRequestPayload(
            meta=ScanLogRequestMetaCreate(name="test-scan-log-request"),
            spec=ScanLogRequestSpecCreate(
                max_entries=10,
                scan_result_uuid=sample_scan_result_uuid,
            ),
        )

        request = scan_log_request.create_scan_log_request(
            self.client, self.parent_namespace, payload
        )

        assert request is not None, "Should successfully create log request"
        assert request.spec is not None, "Request should have spec"
        assert request.spec.max_entries == 10, "Max entries should match"

        print(f"Created log request: {request.uuid}")
        if request.spec.log_messages:
            print(f"Retrieved {len(request.spec.log_messages)} log messages")

    def test_get_scan_result_logs_helper(self, sample_scan_result_uuid) -> None:
        """Test the convenience helper function."""
        print("\n=== TESTING GET SCAN RESULT LOGS HELPER ===")

        # Use the convenience helper
        logs = scan_log_request.get_scan_result_logs(
            self.client,
            self.parent_namespace,
            sample_scan_result_uuid,
            max_entries=10,
        )

        # Logs may be None or empty list depending on scan result
        if logs is not None:
            print(f"Retrieved {len(logs)} log messages")
            for log in logs[:3]:  # Show first 3
                if log.timestamp and log.level:
                    print(f"  {log.timestamp} [{log.level}]")

    @pytest.mark.writes
    def test_scan_log_request_with_filters(self, sample_scan_result_uuid) -> None:
        """Test creating log request with various filters.

        Local-only: scan log request creation requires elevated permissions (403 in CI).
        """
        print("\n=== TESTING SCAN LOG REQUEST WITH FILTERS ===")

        # Test with log level filter
        payload = CreateScanLogRequestPayload(
            meta=ScanLogRequestMetaCreate(name="test-filtered-log-request"),
            spec=ScanLogRequestSpecCreate(
                max_entries=20,
                scan_result_uuid=sample_scan_result_uuid,
                log_levels=[ScanLogLevel.ERROR, ScanLogLevel.WARNING],
                newest_first=True,
            ),
        )

        request = scan_log_request.create_scan_log_request(
            self.client, self.parent_namespace, payload
        )

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
        from endorlabs.exceptions import ValidationError

        payload = CreateScanLogRequestPayload(
            meta=ScanLogRequestMetaCreate(name="test-invalid-uuid-request"),
            spec=ScanLogRequestSpecCreate(
                max_entries=10,
                scan_result_uuid="invalid-uuid",
            ),
        )

        with pytest.raises(ValidationError) as exc_info:
            scan_log_request.create_scan_log_request(
                self.client, self.parent_namespace, payload
            )
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
