"""
Test cases for ScanLogRequest resource operations.

Tests the request-based API for retrieving scan result logs. ScanLogRequest
is a special case - it's not standard CRUD, but a request-based API that
returns logs in the response.
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import scan_log_request, scan_result
from endor_cockpit.resources.scan_log_request import (
    CreateScanLogRequestPayload,
    ScanLogLevel,
    ScanLogRequestMetaCreate,
    ScanLogRequestSpecCreate,
)
from endor_cockpit.types import ListParameters


@pytest.mark.integration
class TestScanLogRequest:
    """Test cases for ScanLogRequest resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self):
        """Fast setup: client and namespace only (runs before each test)."""
        self.client = APIClient(auth_method="api-key")
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.tgowan-endor")

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
        Only fetches 1 item for fast setup. Tests that need sample data should
        request this fixture explicitly.
        """
        # Get a scan result to test log retrieval
        scan_results = scan_result.list_scan_results(
            self.client,
            self.parent_namespace,
            list_params=ListParameters(page_size=1),
            max_pages=1,
        )
        if not scan_results:
            pytest.skip("No scan results available for testing")
        return scan_results[0].uuid

    def test_create_scan_log_request(self, sample_scan_result_uuid):
        """Test creating a scan log request."""
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

    def test_get_scan_result_logs_helper(self, sample_scan_result_uuid):
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

    def test_scan_log_request_with_filters(self, sample_scan_result_uuid):
        """Test creating log request with various filters."""
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

    def test_scan_log_request_error_handling(self):
        """Test error handling for invalid scan result UUID."""
        print("\n=== TESTING ERROR HANDLING ===")

        # Test with invalid scan result UUID
        payload = CreateScanLogRequestPayload(
            meta=ScanLogRequestMetaCreate(name="test-invalid-uuid-request"),
            spec=ScanLogRequestSpecCreate(
                max_entries=10,
                scan_result_uuid="invalid-uuid",
            ),
        )

        request = scan_log_request.create_scan_log_request(
            self.client, self.parent_namespace, payload
        )

        # Request may succeed but return empty logs, or fail
        # Either way, we should handle it gracefully
        if request:
            print("Request created (may have empty logs)")

    def test_scan_log_level_enum(self):
        """Test ScanLogLevel enum values."""
        print("\n=== TESTING SCAN LOG LEVEL ENUM ===")

        # Test enum values
        assert ScanLogLevel.ERROR == "LOG_LEVEL_ERROR"
        assert ScanLogLevel.WARNING == "LOG_LEVEL_WARNING"
        assert ScanLogLevel.INFO == "LOG_LEVEL_INFO"
        assert ScanLogLevel.DEBUG == "LOG_LEVEL_DEBUG"

        print("All log level enum values validated")
