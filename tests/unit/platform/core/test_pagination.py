"""Test cases for automatic pagination functionality.

Tests the automatic pagination feature in BaseResourceOperations.list()
to ensure all pages are fetched correctly.

Refactored: TestPagination and TestListParametersSerialization use a plain
Mock client with get_all mocked — no real APIClient or credentials required.
TestGetAllPageIdPagination exercises the real APIClient.get_all generator with
client.get patched (no network).
"""

from unittest.mock import Mock, patch

from pydantic import BaseModel, Field

from endorlabs.api_client import APIClient
from endorlabs.core.types import ListParameters
from endorlabs.operations import BaseResourceOperations
from tests.conftest import TEST_MAX_PAGES, TEST_PAGE_SIZE


class TestPagination:
    """Test cases for automatic pagination functionality.

    BaseResourceOperations.list() delegates to client.get_all() for pagination.
    We mock get_all to return an iterator of raw dicts.
    """

    def _make_client_with_items(self, items: list[dict]) -> Mock:
        """Create a mock client whose get_all returns *items* as an iterator."""
        client = Mock()
        client.get_all = Mock(return_value=iter(items))
        return client

    def test_pagination_single_item(self) -> None:
        """Pagination with 1 item returns 1 model; get_all called once."""
        items = [{"uuid": "1", "meta": {"name": "item1"}}]
        client = self._make_client_with_items(items)

        ops = BaseResourceOperations(client, "test-resources", Mock)
        results = ops.list(
            "test.namespace",
            list_params=ListParameters(page_size=TEST_PAGE_SIZE),
            max_pages=TEST_MAX_PAGES,
        )

        assert len(results) == 1, f"Expected 1 item, got {len(results)}"
        assert results[0].uuid == "1"
        client.get_all.assert_called_once()

    def test_pagination_with_empty_response(self) -> None:
        """Test pagination with empty response (1 page, 0 count)."""
        client = self._make_client_with_items([])

        ops = BaseResourceOperations(client, "test-resources", Mock)
        results = ops.list(
            "test.namespace",
            list_params=ListParameters(page_size=TEST_PAGE_SIZE),
            max_pages=TEST_MAX_PAGES,
        )

        assert len(results) == 0, f"Expected 0 items, got {len(results)}"
        client.get_all.assert_called_once()

    def test_sort_params_serialize_sort_by_desc(self) -> None:
        """Sort params serialize to list_parameters.sort.path and sort.order (enum)."""
        client = Mock()
        ops = BaseResourceOperations(client, "test-resources", Mock)
        list_params = ListParameters(
            sort_by="meta.create_time",
            desc=True,
        )
        params = ops._build_params(list_params)
        assert params.get("list_parameters.sort.path") == "meta.create_time"
        assert params.get("list_parameters.sort.order") == "SORT_ENTRY_ORDER_DESC"

    def test_sort_params_serialize_sort_by_asc(self) -> None:
        """Sort params with desc=False emit SORT_ENTRY_ORDER_ASC."""
        client = Mock()
        ops = BaseResourceOperations(client, "test-resources", Mock)
        list_params = ListParameters(
            sort_by="meta.name",
            desc=False,
        )
        params = ops._build_params(list_params)
        assert params.get("list_parameters.sort.path") == "meta.name"
        assert params.get("list_parameters.sort.order") == "SORT_ENTRY_ORDER_ASC"

    def test_sort_params_fallback_sort_field_sort_order(self) -> None:
        """Legacy sort_field + sort_order map to sort.path and sort.order (enum)."""
        import warnings

        client = Mock()
        ops = BaseResourceOperations(client, "test-resources", Mock)
        list_params = ListParameters(
            sort_field="meta.create_time",
            sort_order="descending",
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            params = ops._build_params(list_params)
            assert any(
                issubclass(warning.category, DeprecationWarning)
                and "sort_field" in str(warning.message)
                for warning in w
            ), "Expected DeprecationWarning for sort_field/sort_order"
        assert params.get("list_parameters.sort.path") == "meta.create_time"
        assert params.get("list_parameters.sort.order") == "SORT_ENTRY_ORDER_DESC"


class TestListParametersSerialization:
    """Test that new ListParameters fields serialize to list_parameters.*."""

    def test_archive_list_all_serialize_as_booleans(self) -> None:
        """archive and list_all serialize to list_parameters.* as true/false."""
        client = Mock()
        ops = BaseResourceOperations(client, "test-resources", Mock)
        params = ops._build_params(ListParameters(archive=True, list_all=True))
        assert params.get("list_parameters.archive") == "true"
        assert params.get("list_parameters.list_all") == "true"

    def test_page_id_pr_uuid_serialize(self) -> None:
        """page_id and pr_uuid serialize to list_parameters.*."""
        client = Mock()
        ops = BaseResourceOperations(client, "test-resources", Mock)
        params = ops._build_params(ListParameters(page_id="cursor-1", pr_uuid="pr-abc"))
        assert params.get("list_parameters.page_id") == "cursor-1"
        assert params.get("list_parameters.pr_uuid") == "pr-abc"

    def test_group_params_serialize(self) -> None:
        """group_aggregation_paths and group_* serialize to list_parameters.*."""
        client = Mock()
        ops = BaseResourceOperations(client, "test-resources", Mock)
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
    """Test get_all() uses page_id when API returns next_page_id.

    These tests create a real APIClient (api-key auth) but patch client.get
    so no network call is made.  This is needed because get_all is a generator
    method on the real APIClient that cannot be exercised through a Mock.
    """

    def test_get_all_uses_page_id_when_response_has_next_page_id(self) -> None:
        """When response has next_page_id only, next request uses page_id."""
        client = APIClient(auth_method="api-key", key="fake", secret="fake")
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
        client = APIClient(auth_method="api-key", key="fake", secret="fake")
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
        client = APIClient(auth_method="api-key", key="fake", secret="fake")
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


class TestCount:
    """Test count() behavior and list parameter handling."""

    def test_count_does_not_mutate_caller_list_params(self) -> None:
        """count() should not change the caller-owned ListParameters instance."""
        client = Mock()
        response_payload = {"list": {"response": {"total": 3}}}
        client.get = Mock(return_value=Mock(json=Mock(return_value=response_payload)))
        ops = BaseResourceOperations(client, "test-resources", Mock)
        list_params = ListParameters(filter="meta.name==demo")
        assert list_params.count is None

        total = ops.count("tenant.ns", list_params=list_params)

        assert total == 3
        # Regression guard: count() must not mutate caller object.
        assert list_params.count is None
