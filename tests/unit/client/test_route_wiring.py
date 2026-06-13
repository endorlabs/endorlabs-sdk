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


def test_finding_list_for_context_delegates_to_execute_route(
    client_with_mock_transport: Client,
) -> None:
    client = client_with_mock_transport
    scan = SimpleNamespace(
        uuid="scan-1",
        tenant_meta=SimpleNamespace(namespace=TEST_NAMESPACE_DEFAULT),
        context=SimpleNamespace(type="CONTEXT_TYPE_MAIN", id="main"),
    )
    route_result = Mock(values=[])
    with patch.object(
        client.Finding,
        "_execute_route",
        return_value=route_result,
    ) as execute:
        client.Finding.list_for_context(scan, max_pages=2)
        execute.assert_called_once_with(
            "scan.findings",
            source=scan,
            max_pages=2,
        )


def test_dependency_metadata_list_for_context_uses_mixin_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = Mock(spec=endorlabs.api_client.APIClient)
    client = endorlabs.Client(api_client=mock, tenant=TEST_NAMESPACE_DEFAULT)
    scan = SimpleNamespace(
        uuid="scan-1",
        tenant_meta=SimpleNamespace(namespace=TEST_NAMESPACE_DEFAULT),
        context=SimpleNamespace(type="CONTEXT_TYPE_MAIN", id="main"),
    )
    route_result = Mock(values=[])
    with patch.object(
        client.DependencyMetadata,
        "_execute_route",
        return_value=route_result,
    ) as execute:
        client.DependencyMetadata.list_for_context(scan)
        execute.assert_called_once_with(
            "scan.dependency_metadata",
            source=scan,
        )


def test_scan_result_list_by_project_uses_parent_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = Mock(spec=endorlabs.api_client.APIClient)
    client = endorlabs.Client(api_client=mock, tenant=TEST_NAMESPACE_DEFAULT)
    project = SimpleNamespace(
        uuid="proj-1",
        tenant_meta=SimpleNamespace(namespace=TEST_NAMESPACE_DEFAULT),
    )
    route_result = Mock(values=[], edge_used="project.scan_results", warnings=[])
    with patch.object(
        client.ScanResult,
        "_execute_route",
        return_value=route_result,
    ) as execute:
        client.ScanResult.list_by_project(project, limit=5)
        execute.assert_called_once()
        call = execute.call_args
        assert call.args[0] == "project.scan_results"
        assert call.kwargs["source"] is project
        assert call.kwargs["page_size"] == 5


def test_package_version_list_by_project_delegates_to_execute_route(
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
        client.PackageVersion,
        "_execute_route",
        return_value=route_result,
    ) as execute:
        result = client.PackageVersion.list_by_project(project, max_pages=1)
        execute.assert_called_once_with(
            "project.package_versions",
            source=project,
            max_pages=1,
        )
        assert result is route_result
