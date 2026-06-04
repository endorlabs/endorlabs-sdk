"""Test cases for FindingLog resource operations.

Tests LIST/GET and filtering by operation type for FindingLog resources.
"""

import pytest

import endorlabs
from endorlabs.api_client import APIClient
from endorlabs.core.exceptions import ServerError
from tests.conftest import TEST_LOG_LIST_MAX_PAGES, TEST_NAMESPACE_DEFAULT
from tests.integration.conftest import (
    assert_bounded_log_rows,
    bounded_log_list_params,
    log_list_kwargs,
)


@pytest.mark.integration
@pytest.mark.long
class TestFindingLog:
    """Test cases for FindingLog resource operations."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace, root_namespace) -> None:
        """Fast setup: client and namespace from conftest."""
        self.client = api_client
        self.namespace = namespace
        self.root_namespace = root_namespace
        self.endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.created_finding_log_uuids: list[str] = []

    def teardown_method(self) -> None:
        """Clean up any resources created during tests."""
        for uuid in self.created_finding_log_uuids:
            try:
                self.endor_client.FindingLog.delete(uuid)
            except Exception as e:
                print(f"Warning: Failed to delete finding log {uuid}: {e}")
        self.created_finding_log_uuids.clear()

    def test_finding_log_list(self) -> None:
        """LIST in namespace with bounded pagination (no traverse)."""
        result = self.endor_client.FindingLog.list(**log_list_kwargs())
        assert isinstance(result, list)
        assert_bounded_log_rows(result)

    def test_finding_log_get(self) -> None:
        """GET first item from bounded LIST in namespace."""
        items = self.endor_client.FindingLog.list(**log_list_kwargs())
        assert_bounded_log_rows(items)
        if not items:
            pytest.skip("No resources in scope (empty; may be filter/auth/scope)")
        got = self.endor_client.FindingLog.get(items[0])
        assert got is not None
        assert got.uuid == items[0].uuid

    def test_finding_log_list_by_operation_create(self) -> None:
        """Filter finding logs by CREATE operation (bounded)."""
        try:
            logs = self.endor_client.FindingLog.list(
                list_params=bounded_log_list_params(
                    filter_expr="spec.operation==OPERATION_CREATE",
                ),
                max_pages=TEST_LOG_LIST_MAX_PAGES,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        assert isinstance(logs, list)
        assert_bounded_log_rows(logs)
        for log in logs:
            assert (
                log.spec.operation == "OPERATION_CREATE"
                or str(log.spec.operation) == "OPERATION_CREATE"
            )

    def test_finding_log_list_by_operation_update(self) -> None:
        """Filter finding logs by UPDATE operation (bounded)."""
        try:
            logs = self.endor_client.FindingLog.list(
                list_params=bounded_log_list_params(
                    filter_expr="spec.operation==OPERATION_UPDATE",
                ),
                max_pages=TEST_LOG_LIST_MAX_PAGES,
            )
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        assert isinstance(logs, list)
        assert_bounded_log_rows(logs)
        for log in logs:
            assert (
                log.spec.operation == "OPERATION_UPDATE"
                or str(log.spec.operation) == "OPERATION_UPDATE"
            )

    def test_finding_log_update_raises_not_implemented(self) -> None:
        """When update_fn is None, FindingLog.update raises NotImplementedError."""
        from unittest.mock import Mock

        mock = Mock(spec=APIClient)
        client = endorlabs.Client(
            api_client=mock,
            tenant=TEST_NAMESPACE_DEFAULT,
        )
        with pytest.raises(NotImplementedError, match="does not support update"):
            client.FindingLog.update("dummy-uuid", {}, update_mask="meta.description")
