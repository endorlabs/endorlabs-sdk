"""Tests for the resource-oriented Client facade (TDD).

Verifies delegation, namespace resolution, and convenience kwargs
for endorlabs.Client and client.namespaces. Aligns with recommended UX
(import endorlabs; client = endorlabs.Client(...)) and registry-driven architecture.

Delegation is asserted by injecting a mock into the facade's _list_fn (noqa: SLF001);
module-boundary mocking would require resolving callables at call time (lazy registry).
"""

from unittest.mock import Mock, patch

import conftest
import pytest

import endorlabs
from endorlabs.api_client import APIClient
from endorlabs.client_surface import Client
from endorlabs.facade import ScanLogsFacade


@pytest.fixture
def client_with_mock_transport() -> Client:
    """Client with mock APIClient and canonical test namespace (typed fixture)."""
    mock = Mock(spec=APIClient)
    client = endorlabs.Client(
        api_client=mock,
        tenant=conftest.TEST_NAMESPACE_DEFAULT,
    )
    return client


def test_client_requires_namespace_or_tenant_for_list() -> None:
    """When tenant is None and namespace is not passed to list(), raise ValueError."""
    client = endorlabs.Client(api_client=Mock(spec=APIClient), tenant=None)
    # Inject mock for delegation; module-boundary mock would need lazy registry.
    client.namespaces._list_fn = Mock(return_value=[])
    with pytest.raises(ValueError, match="namespace"):
        client.namespaces.list()
    client.namespaces._list_fn.assert_not_called()


def test_client_namespace_list_uses_default_tenant(
    client_with_mock_transport: Client,
) -> None:
    """list(traverse=True, max_pages=1) delegates with tenant, traverse, max_pages."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.namespaces._list_fn = mock_list
    result = client.namespaces.list(traverse=True, max_pages=1)
    assert result == []
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    assert args[0] is client._client
    assert args[1] == conftest.TEST_NAMESPACE_DEFAULT
    assert args[2] is not None
    assert args[2].traverse is True
    assert args[3] == 1


def test_client_namespace_list_override_namespace(
    client_with_mock_transport: Client,
) -> None:
    """client.namespaces.list(namespace='bar') uses 'bar' instead of default tenant."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.namespaces._list_fn = mock_list
    client.namespaces.list(namespace="bar", max_pages=1)
    args, _ = mock_list.call_args
    assert args[1] == "bar"
    assert args[3] == 1


def test_client_creates_apiclient_when_not_passed() -> None:
    """Client(tenant=...) without api_client creates an APIClient internally."""
    with patch("endorlabs.client_surface.APIClient") as mock_apiclient_class:
        mock_apiclient_class.return_value = Mock(spec=APIClient)
        client = endorlabs.Client(tenant=conftest.TEST_NAMESPACE_DEFAULT)
        client.namespaces._list_fn = Mock(return_value=[])
        _ = client.namespaces.list(max_pages=1)
        mock_apiclient_class.assert_called_once()
    assert mock_apiclient_class.return_value is not None


def test_client_namespace_list_convenience_kwargs(
    client_with_mock_transport: Client,
) -> None:
    """list(traverse, page_size=10, max_pages=2) builds ListParams; max_pages passed."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.namespaces._list_fn = mock_list
    client.namespaces.list(traverse=True, page_size=10, max_pages=2)
    args, _ = mock_list.call_args
    lp = args[2]
    assert lp is not None
    assert lp.traverse is True
    assert lp.page_size == 10
    assert args[3] == 2


def test_client_projects_present_and_delegates(
    client_with_mock_transport: Client,
) -> None:
    """client.projects is present and list(traverse=True, max_pages=1) delegates."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.projects._list_fn = mock_list
    result = client.projects.list(traverse=True, max_pages=1)
    assert result == []
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    assert args[0] is client._client
    assert args[1] == conftest.TEST_NAMESPACE_DEFAULT
    assert args[2] is not None
    assert args[2].traverse is True
    assert args[3] == 1


def test_client_api_keys_update_raises_not_implemented(
    client_with_mock_transport: Client,
) -> None:
    """client.api_keys.update() raises NotImplementedError (resource has no update)."""
    client = client_with_mock_transport
    with pytest.raises(NotImplementedError, match="does not support update"):
        client.api_keys.update("id", {}, "mask")


def test_client_exposes_all_registry_resources(
    client_with_mock_transport: Client,
) -> None:
    """Client exposes exactly the resources defined in RESOURCE_REGISTRY."""
    from endorlabs.facade import ResourceFacade
    from endorlabs.registry import RESOURCE_REGISTRY

    client = client_with_mock_transport
    for entry in RESOURCE_REGISTRY:
        assert hasattr(client, entry.attr_name), f"Missing attribute: {entry.attr_name}"
        facade = getattr(client, entry.attr_name)
        assert isinstance(facade, ResourceFacade), (
            f"{entry.attr_name} is not a ResourceFacade"
        )
        assert hasattr(facade, "list")
        assert hasattr(facade, "get")


def test_client_exposes_all_custom_facades(
    client_with_mock_transport: Client,
) -> None:
    """Client exposes exactly the facades defined in CUSTOM_FACADE_REGISTRY."""
    from endorlabs.registry import CUSTOM_FACADE_REGISTRY

    client = client_with_mock_transport
    for entry in CUSTOM_FACADE_REGISTRY:
        assert hasattr(client, entry.attr_name), f"Missing attribute: {entry.attr_name}"
        facade = getattr(client, entry.attr_name)
        assert facade is not None, f"{entry.attr_name} is None"


def test_client_namespace_list_uses_session_logging_only(
    client_with_mock_transport: Client,
) -> None:
    """list() delegates with no logging_level; session logging is set on client."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.namespaces._list_fn = mock_list
    client.namespaces.list(max_pages=1)
    mock_list.assert_called_once()
    args, kwargs = mock_list.call_args
    assert len(args) == 4
    assert "logging_level" not in kwargs


def test_client_scan_logs_facade_present_and_delegates(
    client_with_mock_transport: Client,
) -> None:
    """client.scan_logs present; get_logs delegates to get_scan_result_logs."""
    client = client_with_mock_transport
    assert hasattr(client, "scan_logs")
    assert isinstance(client.scan_logs, ScanLogsFacade)
    with patch(
        "endorlabs.resources.scan_log_request.get_scan_result_logs",
        return_value=[],
    ) as mock_get_logs:
        result = client.scan_logs.get_logs("scan-result-uuid-123")
        assert result == []
        mock_get_logs.assert_called_once()
        args, kwargs = mock_get_logs.call_args
        assert args[0] is client._client
        assert args[1] == conftest.TEST_NAMESPACE_DEFAULT
        assert args[2] == "scan-result-uuid-123"
        assert kwargs.get("max_entries") == 100
