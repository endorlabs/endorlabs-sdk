"""Unit tests for SupportedToolChainVersionFacade (no live API)."""

from __future__ import annotations

from unittest.mock import MagicMock

from endorlabs.facade.specialized import SupportedToolChainVersionFacade


def test_list_uses_public_get_all_not_private_client() -> None:
    api = MagicMock()
    api.get_all.return_value = iter([{"uuid": "t1", "spec": {}}])
    facade = SupportedToolChainVersionFacade(api, default_namespace="example-tenant")
    rows = facade.list(filter='spec.os=="linux"', max_pages=2)
    assert rows == [{"uuid": "t1", "spec": {}}]
    url, kwargs = api.get_all.call_args[0][0], api.get_all.call_args[1]
    assert url == "v1/namespaces/system/supported-toolchain-versions"
    assert kwargs["params"]["list_parameters.filter"] == 'spec.os=="linux"'
    assert kwargs["max_pages"] == 2


def test_list_respects_namespace_override() -> None:
    api = MagicMock()
    api.get_all.return_value = iter([])
    facade = SupportedToolChainVersionFacade(api, None)
    _ = facade.list(namespace="example-tenant")
    assert api.get_all.call_args[0][0].startswith(
        "v1/namespaces/example-tenant/supported-toolchain-versions"
    )
