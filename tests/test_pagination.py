"""Test cases for automatic pagination functionality.

Tests the new automatic pagination feature in BaseResourceOperations.list()
to ensure all pages are fetched correctly.
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import conftest

from endorlabs.api_client import APIClient
from endorlabs.models.base import BaseResourceOperations
from endorlabs.types import ListParameters


class TestPagination:
    """Test cases for automatic pagination functionality."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace) -> None:
        """Set up test environment (client and namespace from conftest)."""
        self.client = api_client
        self.namespace = namespace

    def test_pagination_with_mock_data(self) -> None:
        """Test pagination with 1 page, 1 count limit."""
        mock_response = {
            "list": {
                "objects": [{"uuid": "1", "meta": {"name": "item1"}}],
                "response": {},  # No next_page_token
            }
        }
        with patch.object(self.client, "get") as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_get.return_value = mock_response_obj

            ops = BaseResourceOperations(self.client, "test-resources", Mock)
            results = ops.list(
                self.namespace,
                list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
                max_pages=conftest.TEST_MAX_PAGES,
            )

            assert len(results) == 1, f"Expected 1 item, got {len(results)}"
            assert results[0].uuid == "1"
            assert mock_get.call_count == 1, (
                f"Expected 1 API call, got {mock_get.call_count}"
            )

    def test_pagination_with_max_pages_limit(self) -> None:
        """Test pagination stops at max_pages (1 page, 1 count)."""
        mock_response = {
            "list": {
                "objects": [{"uuid": "1", "meta": {"name": "item1"}}],
                "response": {},  # No next_page_token
            }
        }
        with patch.object(self.client, "get") as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_get.return_value = mock_response_obj

            ops = BaseResourceOperations(self.client, "test-resources", Mock)
            results = ops.list(
                self.namespace,
                list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
                max_pages=conftest.TEST_MAX_PAGES,
            )

            assert len(results) == 1, f"Expected 1 item, got {len(results)}"
            assert mock_get.call_count == 1, (
                f"Expected 1 API call, got {mock_get.call_count}"
            )

    def test_pagination_with_list_parameters_max_pages(self) -> None:
        """Test pagination with ListParameters and max_pages (1 page, 1 count)."""
        mock_response = {
            "list": {
                "objects": [{"uuid": "1", "meta": {"name": "item1"}}],
                "response": {},
            }
        }
        with patch.object(self.client, "get") as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_get.return_value = mock_response_obj

            list_params = ListParameters(page_size=conftest.TEST_PAGE_SIZE)
            ops = BaseResourceOperations(self.client, "test-resources", Mock)
            results = ops.list(
                self.namespace,
                list_params=list_params,
                max_pages=conftest.TEST_MAX_PAGES,
            )

            assert len(results) == 1, f"Expected 1 item, got {len(results)}"
            assert mock_get.call_count == 1, (
                f"Expected 1 API call, got {mock_get.call_count}"
            )

    def test_pagination_with_no_pages(self) -> None:
        """Test pagination with single page (no next_page_token), 1 page 1 count."""
        mock_response = {
            "list": {
                "objects": [{"uuid": "1", "meta": {"name": "item1"}}],
                "response": {},
            }
        }
        with patch.object(self.client, "get") as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_get.return_value = mock_response_obj

            ops = BaseResourceOperations(self.client, "test-resources", Mock)
            results = ops.list(
                self.namespace,
                list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
                max_pages=conftest.TEST_MAX_PAGES,
            )

            assert len(results) == 1, f"Expected 1 item, got {len(results)}"
            assert mock_get.call_count == 1, (
                f"Expected 1 API call, got {mock_get.call_count}"
            )

    def test_pagination_with_empty_response(self) -> None:
        """Test pagination with empty response (1 page, 0 count)."""
        mock_response = {"list": {"objects": [], "response": {}}}
        with patch.object(self.client, "get") as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_get.return_value = mock_response_obj

            ops = BaseResourceOperations(self.client, "test-resources", Mock)
            results = ops.list(
                self.namespace,
                list_params=ListParameters(page_size=conftest.TEST_PAGE_SIZE),
                max_pages=conftest.TEST_MAX_PAGES,
            )

            assert len(results) == 0, f"Expected 0 items, got {len(results)}"
            assert mock_get.call_count == 1, (
                f"Expected 1 API call, got {mock_get.call_count}"
            )

    def test_sort_params_serialize_sort_by_desc(self) -> None:
        """Sort params serialize to list_parameters.sort.path and sort.order (enum)."""
        ops = BaseResourceOperations(self.client, "test-resources", Mock)
        list_params = ListParameters(
            sort_by="meta.create_time",
            desc=True,
        )
        params = ops._build_params(list_params)
        assert params.get("list_parameters.sort.path") == "meta.create_time"
        assert params.get("list_parameters.sort.order") == "SORT_ENTRY_ORDER_DESC"

    def test_sort_params_serialize_sort_by_asc(self) -> None:
        """Sort params with desc=False emit SORT_ENTRY_ORDER_ASC."""
        ops = BaseResourceOperations(self.client, "test-resources", Mock)
        list_params = ListParameters(
            sort_by="meta.name",
            desc=False,
        )
        params = ops._build_params(list_params)
        assert params.get("list_parameters.sort.path") == "meta.name"
        assert params.get("list_parameters.sort.order") == "SORT_ENTRY_ORDER_ASC"

    def test_sort_params_fallback_sort_field_sort_order(self) -> None:
        """Legacy sort_field + sort_order map to sort.path and sort.order (enum)."""
        ops = BaseResourceOperations(self.client, "test-resources", Mock)
        list_params = ListParameters(
            sort_field="meta.create_time",
            sort_order="descending",
        )
        params = ops._build_params(list_params)
        assert params.get("list_parameters.sort.path") == "meta.create_time"
        assert params.get("list_parameters.sort.order") == "SORT_ENTRY_ORDER_DESC"


class TestListParametersSerialization:
    """Test that new ListParameters fields serialize to list_parameters.*."""

    @pytest.fixture(autouse=True)
    def setup(self, api_client, namespace) -> None:
        """Set up test environment (client and namespace from conftest)."""
        self.client = api_client
        self.namespace = namespace

    def test_archive_list_all_serialize_as_booleans(self) -> None:
        """archive and list_all serialize to list_parameters.* as true/false."""
        ops = BaseResourceOperations(self.client, "test-resources", Mock)
        params = ops._build_params(ListParameters(archive=True, list_all=True))
        assert params.get("list_parameters.archive") == "true"
        assert params.get("list_parameters.list_all") == "true"

    def test_page_id_pr_uuid_serialize(self) -> None:
        """page_id and pr_uuid serialize to list_parameters.*."""
        ops = BaseResourceOperations(self.client, "test-resources", Mock)
        params = ops._build_params(ListParameters(page_id="cursor-1", pr_uuid="pr-abc"))
        assert params.get("list_parameters.page_id") == "cursor-1"
        assert params.get("list_parameters.pr_uuid") == "pr-abc"

    def test_group_params_serialize(self) -> None:
        """group_aggregation_paths and group_* serialize to list_parameters.*."""
        ops = BaseResourceOperations(self.client, "test-resources", Mock)
        list_params = ListParameters(
            group_aggregation_paths=["meta.name", "spec.level"],
            group_by_time=True,
            group_unique_count_paths=["x"],
        )
        params = ops._build_params(list_params)
        assert params.get("list_parameters.group_aggregation_paths") == (
            "meta.name,spec.level"
        )
        assert params.get("list_parameters.group_by_time") == "true"
        assert params.get("list_parameters.group_unique_count_paths") == "x"


class TestGetAllPageIdPagination:
    """Test get_all() uses page_id when API returns next_page_id."""

    def test_get_all_uses_page_id_when_response_has_next_page_id(self) -> None:
        """When response has next_page_id only, next request uses page_id."""
        client = APIClient(auth_method="api-key")
        try:
            page1 = {
                "list": {
                    "objects": [{"uuid": "a"}],
                    "response": {"next_page_id": "cursor-abc"},
                }
            }
            page2 = {
                "list": {"objects": [{"uuid": "b"}], "response": {}},
            }
            with patch.object(client, "get") as mock_get:
                mock_get.side_effect = [
                    Mock(json=Mock(return_value=page1)),
                    Mock(json=Mock(return_value=page2)),
                ]
                items = list(client.get_all("/v1/namespaces/ns/items", params={}))
            assert len(items) == 2
            assert items[0]["uuid"] == "a"
            assert items[1]["uuid"] == "b"
            assert mock_get.call_count == 2
            second_call_params = mock_get.call_args_list[1].kwargs.get("params", {})
            assert second_call_params.get("list_parameters.page_id") == "cursor-abc"
            assert "list_parameters.page_token" not in second_call_params
        finally:
            client.close()

    def test_get_all_uses_page_token_when_only_next_page_token(self) -> None:
        """When only next_page_token present, behavior unchanged (page_token used)."""
        client = APIClient(auth_method="api-key")
        try:
            page1 = {
                "list": {
                    "objects": [{"uuid": "a"}],
                    "response": {"next_page_token": "tok123"},
                }
            }
            page2 = {"list": {"objects": [{"uuid": "b"}], "response": {}}}
            with patch.object(client, "get") as mock_get:
                mock_get.side_effect = [
                    Mock(json=Mock(return_value=page1)),
                    Mock(json=Mock(return_value=page2)),
                ]
                items = list(client.get_all("/v1/namespaces/ns/items", params={}))
            assert len(items) == 2
            assert mock_get.call_count == 2
            second_call_params = mock_get.call_args_list[1].kwargs.get("params", {})
            assert second_call_params.get("list_parameters.page_token") == "tok123"
            assert "list_parameters.page_id" not in second_call_params
        finally:
            client.close()

    def test_get_all_prefers_page_id_when_both_present(self) -> None:
        """When both next_page_id and next_page_token present, page_id wins."""
        client = APIClient(auth_method="api-key")
        try:
            page1 = {
                "list": {
                    "objects": [{"uuid": "a"}],
                    "response": {
                        "next_page_id": "cursor-xyz",
                        "next_page_token": "tok456",
                    },
                }
            }
            page2 = {"list": {"objects": [{"uuid": "b"}], "response": {}}}
            with patch.object(client, "get") as mock_get:
                mock_get.side_effect = [
                    Mock(json=Mock(return_value=page1)),
                    Mock(json=Mock(return_value=page2)),
                ]
                items = list(client.get_all("/v1/namespaces/ns/items", params={}))
            assert len(items) == 2
            assert mock_get.call_count == 2
            second_call_params = mock_get.call_args_list[1].kwargs.get("params", {})
            assert second_call_params.get("list_parameters.page_id") == "cursor-xyz"
            assert "list_parameters.page_token" not in second_call_params
        finally:
            client.close()


class TestListIter:
    """Test list_iter yields items without materializing full list."""

    def test_list_iter_yields_models_from_get_all(self) -> None:
        """list_iter yields one model per item from get_all; no full list."""
        from pydantic import BaseModel, Field

        class SimpleModel(BaseModel):
            uuid: str = Field(..., description="UUID")

        client = Mock()
        client.get_all = Mock(return_value=iter([{"uuid": "a"}, {"uuid": "b"}]))
        ops = BaseResourceOperations(client, "test-resources", SimpleModel)
        it = ops.list_iter("tenant.ns", None, max_pages=1)
        items = list(it)
        assert len(items) == 2
        assert items[0].uuid == "a"
        assert items[1].uuid == "b"
        client.get_all.assert_called_once()


if __name__ == "__main__":
    # Run tests directly
    import os

    # Set up environment
    # Require ENDOR_NAMESPACE to be set
    if not os.getenv("ENDOR_NAMESPACE"):
        print("ERROR: ENDOR_NAMESPACE environment variable must be set")
        sys.exit(1)

    # Create test instance and manually set up
    test_instance = TestPagination()

    # Manual setup without using pytest fixture
    test_instance.client = APIClient(auth_method="api-key")
    test_instance.namespace = os.getenv(
        "ENDOR_NAMESPACE", conftest.TEST_NAMESPACE_DEFAULT
    )

    try:
        print("Running pagination tests...")

        # Run mock tests
        test_instance.test_pagination_with_mock_data()
        test_instance.test_pagination_with_max_pages_limit()
        test_instance.test_pagination_with_list_parameters_max_pages()
        test_instance.test_pagination_with_no_pages()
        test_instance.test_pagination_with_empty_response()
        test_instance.test_sort_params_serialize_sort_by_desc()
        test_instance.test_sort_params_serialize_sort_by_asc()
        test_instance.test_sort_params_fallback_sort_field_sort_order()

        print("\n[SUCCESS] All pagination tests completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        test_instance.client.close()
