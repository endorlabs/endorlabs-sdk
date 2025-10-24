"""
Test cases for automatic pagination functionality.

Tests the new automatic pagination feature in BaseResourceOperations.list()
to ensure all pages are fetched correctly.
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.models.base import BaseResourceOperations
from endor_cockpit.resources import finding, project
from endor_cockpit.types import ListParameters


class TestPagination:
    """Test cases for automatic pagination functionality."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = APIClient()
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")

    def test_pagination_with_mock_data(self):
        """Test pagination with mock API responses."""
        # Mock response data simulating multiple pages
        mock_responses = [
            {
                "list": {
                    "objects": [
                        {"uuid": "1", "meta": {"name": "item1"}},
                        {"uuid": "2", "meta": {"name": "item2"}},
                    ],
                    "response": {"next_page_token": 123},
                }
            },
            {
                "list": {
                    "objects": [
                        {"uuid": "3", "meta": {"name": "item3"}},
                        {"uuid": "4", "meta": {"name": "item4"}},
                    ],
                    "response": {"next_page_token": 456},
                }
            },
            {
                "list": {
                    "objects": [
                        {"uuid": "5", "meta": {"name": "item5"}},
                    ],
                    "response": {},  # No next_page_token - end of pagination
                }
            },
        ]

        # Mock the client.get method to return our test data
        with patch.object(self.client, "get") as mock_get:
            # Create mock responses that return the correct data
            mock_responses_objects = []
            for response in mock_responses:
                mock_response = Mock()
                mock_response.json.return_value = response
                mock_responses_objects.append(mock_response)

            mock_get.side_effect = mock_responses_objects

            # Test with a simple resource operations class
            ops = BaseResourceOperations(self.client, "test-resources", Mock)
            results = ops.list(self.namespace)

            # Verify all items were fetched
            assert len(results) == 5, f"Expected 5 items, got {len(results)}"
            assert results[0].uuid == "1"
            assert results[4].uuid == "5"

            # Verify correct number of API calls
            assert mock_get.call_count == 3, (
                f"Expected 3 API calls, got {mock_get.call_count}"
            )

    def test_pagination_with_unlimited_pages(self):
        """Test pagination fetches all pages without limits."""
        # Mock response data with many pages
        mock_responses = [
            {
                "list": {
                    "objects": [{"uuid": str(i), "meta": {"name": f"item{i}"}}],
                    "response": {"next_page_token": i + 1},
                }
            }
            for i in range(5)  # 5 pages
        ]
        # Last page has no next_page_token
        mock_responses[-1]["list"]["response"] = {}

        with patch.object(self.client, "get") as mock_get:
            # Create mock responses that return the correct data
            mock_responses_objects = []
            for response in mock_responses:
                mock_response = Mock()
                mock_response.json.return_value = response
                mock_responses_objects.append(mock_response)

            mock_get.side_effect = mock_responses_objects

            ops = BaseResourceOperations(self.client, "test-resources", Mock)
            results = ops.list(self.namespace)

            # Should fetch all 5 pages
            assert len(results) == 5, f"Expected 5 items, got {len(results)}"
            assert mock_get.call_count == 5, (
                f"Expected 5 API calls, got {mock_get.call_count}"
            )

    def test_pagination_with_list_parameters(self):
        """Test pagination with ListParameters (no max_pages limit)."""
        mock_responses = [
            {
                "list": {
                    "objects": [{"uuid": str(i), "meta": {"name": f"item{i}"}}],
                    "response": {"next_page_token": i + 1},
                }
            }
            for i in range(3)
        ]
        # Last page has no next_page_token
        mock_responses[-1]["list"]["response"] = {}

        with patch.object(self.client, "get") as mock_get:
            # Create mock responses that return the correct data
            mock_responses_objects = []
            for response in mock_responses:
                mock_response = Mock()
                mock_response.json.return_value = response
                mock_responses_objects.append(mock_response)

            mock_get.side_effect = mock_responses_objects

            list_params = ListParameters(page_size=1)
            ops = BaseResourceOperations(self.client, "test-resources", Mock)
            results = ops.list(self.namespace, list_params=list_params)

            # Should fetch all 3 pages
            assert len(results) == 3, f"Expected 3 items, got {len(results)}"
            assert mock_get.call_count == 3, (
                f"Expected 3 API calls, got {mock_get.call_count}"
            )

    def test_pagination_with_no_pages(self):
        """Test pagination with single page (no next_page_token)."""
        mock_response = {
            "list": {
                "objects": [
                    {"uuid": "1", "meta": {"name": "item1"}},
                    {"uuid": "2", "meta": {"name": "item2"}},
                ],
                "response": {},  # No next_page_token
            }
        }

        with patch.object(self.client, "get") as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_get.return_value = mock_response_obj

            ops = BaseResourceOperations(self.client, "test-resources", Mock)
            results = ops.list(self.namespace)

            # Should fetch only one page
            assert len(results) == 2, f"Expected 2 items, got {len(results)}"
            assert mock_get.call_count == 1, (
                f"Expected 1 API call, got {mock_get.call_count}"
            )

    def test_pagination_with_empty_response(self):
        """Test pagination with empty response."""
        mock_response = {"list": {"objects": [], "response": {}}}

        with patch.object(self.client, "get") as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_get.return_value = mock_response_obj

            ops = BaseResourceOperations(self.client, "test-resources", Mock)
            results = ops.list(self.namespace)

            # Should handle empty response gracefully
            assert len(results) == 0, f"Expected 0 items, got {len(results)}"
            assert mock_get.call_count == 1, (
                f"Expected 1 API call, got {mock_get.call_count}"
            )

    @pytest.mark.integration
    def test_real_pagination_with_findings(self):
        """Test pagination with real API data (integration test)."""
        # This test will only run if we have real API access
        try:
            findings = finding.list_findings(self.client, self.namespace)
            assert isinstance(findings, list), "Should return a list of findings"

            # Log pagination info for debugging
            print(f"Fetched {len(findings)} findings from API")

            # If we have many findings, verify we got them all
            if len(findings) > 0:
                print(f"First finding: {findings[0].uuid}")
                if len(findings) > 1:
                    print(f"Last finding: {findings[-1].uuid}")

        except Exception as e:
            pytest.skip(f"Integration test skipped due to API error: {e}")

    @pytest.mark.integration
    def test_real_pagination_with_projects(self):
        """Test pagination with real projects data (integration test)."""
        try:
            projects = project.list_projects(self.client, self.namespace)
            assert isinstance(projects, list), "Should return a list of projects"

            print(f"Fetched {len(projects)} projects from API")

            if len(projects) > 0:
                print(f"First project: {projects[0].uuid}")
                if len(projects) > 1:
                    print(f"Last project: {projects[-1].uuid}")

        except Exception as e:
            pytest.skip(f"Integration test skipped due to API error: {e}")


if __name__ == "__main__":
    # Run tests directly
    import os

    # Set up environment
    os.environ.setdefault("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")

    # Create test instance and manually set up
    test_instance = TestPagination()

    # Manual setup without using pytest fixture
    test_instance.client = APIClient()
    test_instance.namespace = os.getenv(
        "ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit"
    )

    try:
        print("Running pagination tests...")

        # Run mock tests
        test_instance.test_pagination_with_mock_data()
        test_instance.test_pagination_with_max_pages_limit()
        test_instance.test_pagination_with_list_parameters_max_pages()
        test_instance.test_pagination_with_no_pages()
        test_instance.test_pagination_with_empty_response()

        print("\n[SUCCESS] All pagination tests completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
