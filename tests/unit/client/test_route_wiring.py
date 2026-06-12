"""Client-level tests for public route facade methods."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import endorlabs
from tests.conftest import TEST_NAMESPACE_DEFAULT

if TYPE_CHECKING:
    import pytest

    from endorlabs.client_surface import Client


def test_finding_list_by_project_delegates_to_execute_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = Mock(spec=endorlabs.api_client.APIClient)
    client = endorlabs.Client(api_client=mock, tenant=TEST_NAMESPACE_DEFAULT)
    project = SimpleNamespace(
        uuid="proj-1",
        tenant_meta=SimpleNamespace(namespace=TEST_NAMESPACE_DEFAULT),
    )
    route_result = Mock(values=[])
    with patch.object(
        client.Finding,
        "_execute_route",
        return_value=route_result,
    ) as execute:
        result = client.Finding.list_by_project(project, filter='spec.level=="X"')
        execute.assert_called_once_with(
            "project.findings",
            source=project,
            filter='spec.level=="X"',
        )
        assert result is route_result


def test_finding_list_by_scan_delegates_to_execute_route(
    client_with_mock_transport: Client,
) -> None:
    client = client_with_mock_transport
    scan = SimpleNamespace(
        uuid="scan-1",
        tenant_meta=SimpleNamespace(namespace=TEST_NAMESPACE_DEFAULT),
    )
    route_result = Mock(values=[])
    with patch.object(
        client.Finding,
        "_execute_route",
        return_value=route_result,
    ) as execute:
        client.Finding.list_by_scan(scan)
        execute.assert_called_once_with("scan.findings", source=scan)


def test_scan_result_list_by_project_uses_parent_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = Mock(spec=endorlabs.api_client.APIClient)
    client = endorlabs.Client(api_client=mock, tenant=TEST_NAMESPACE_DEFAULT)
    project = SimpleNamespace(
        uuid="proj-1",
        tenant_meta=SimpleNamespace(namespace=TEST_NAMESPACE_DEFAULT),
    )
    mock_list = Mock(return_value=[])
    client.ScanResult._ops.list = mock_list
    with patch.object(
        client.ScanResult, "list", wraps=client.ScanResult.list
    ) as list_mock:
        client.ScanResult.list_by_project(project, limit=5)
        list_mock.assert_called()
        _, kwargs = list_mock.call_args
        assert kwargs.get("parent") is project
