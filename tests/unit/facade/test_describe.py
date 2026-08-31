"""Tests for ListableFacade.describe() live introspection."""

from __future__ import annotations

import inspect
from unittest.mock import Mock

import endorlabs
from endorlabs.api_client import APIClient
from endorlabs.facade.description import list_params_from_signature
from endorlabs.registry import RESOURCE_REGISTRY


def test_finding_describe_has_identity_kwargs_and_routes() -> None:
    mock = Mock(spec=APIClient)
    client = endorlabs.Client(tenant="example-tenant", api_client=mock)
    desc = client.Finding.describe()
    assert desc.attr_name == "Finding"
    assert desc.resource_name == "findings"
    assert ("name", "meta.name") in desc.identity_kwargs
    assert "meta.name" in desc.filterable_fields
    assert "list_by_project" in desc.route_methods
    text = str(desc)
    assert "Finding (findings)" in text
    assert "name -> meta.name" in text
    assert "FacadeDescription(" not in text
    assert mock.mock_calls == []


def test_describe_list_params_match_signature() -> None:
    client = endorlabs.Client(tenant="example-tenant", api_client=Mock(spec=APIClient))
    desc = client.Finding.describe()
    live = list_params_from_signature(type(client.Finding).list)
    assert tuple(p.name for p in desc.list_params) == tuple(p.name for p in live)
    sig = inspect.signature(type(client.Finding).list)
    for param_info in desc.list_params:
        assert param_info.name in sig.parameters


def test_all_registry_facades_describe_without_network() -> None:
    mock = Mock(spec=APIClient)
    client = endorlabs.Client(tenant="example-tenant", api_client=mock)
    for entry in RESOURCE_REGISTRY:
        facade = getattr(client, entry.attr_name)
        if not hasattr(facade, "describe"):
            continue  # custom facades (Query, CallGraphData) are not ListableFacade
        desc = facade.describe()
        assert desc.attr_name == entry.attr_name
        assert desc.resource_name == entry.resource_name
        assert str(desc)
    assert mock.mock_calls == []


def test_oss_facade_not_namespace_scoped() -> None:
    client = endorlabs.Client(tenant="example-tenant", api_client=Mock(spec=APIClient))
    desc = client.Vulnerability.describe()
    assert desc.scope == "oss"
    assert desc.namespace_scoped is False
