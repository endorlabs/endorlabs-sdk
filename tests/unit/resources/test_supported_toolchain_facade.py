"""Unit tests for SupportedToolChainVersionFacade (no live API)."""

from __future__ import annotations

from unittest.mock import MagicMock

from endorlabs.facade.specialized import SupportedToolChainVersionFacade
from endorlabs.operations.pagination import ResourcePage


def _page(items: list[dict[str, object]]) -> ResourcePage[dict[str, object]]:
    return ResourcePage(
        items=tuple(items),
        owner_namespace="system",
        traverse=False,
        requested_page_size=None,
        page_index=0,
        next_cursor=None,
        stop_reason="complete",
        completeness="complete",
        pages_fetched=1,
        items_fetched=len(items),
    )


def test_list_uses_public_iter_pages_not_private_client() -> None:
    api = MagicMock()
    api.iter_pages.return_value = iter([_page([{"uuid": "t1", "spec": {}}])])
    facade = SupportedToolChainVersionFacade(api, default_namespace="example-tenant")
    rows = facade.list(filter='spec.os=="linux"', max_pages=2)
    assert rows == [{"uuid": "t1", "spec": {}}]
    url = api.iter_pages.call_args[0][0]
    kwargs = api.iter_pages.call_args[1]
    assert url == "v1/namespaces/system/supported-toolchain-versions"
    assert kwargs["params"]["list_parameters.filter"] == 'spec.os=="linux"'
    assert kwargs["max_pages"] == 2


def test_list_respects_namespace_override() -> None:
    api = MagicMock()
    api.iter_pages.return_value = iter([_page([])])
    facade = SupportedToolChainVersionFacade(api, None)
    _ = facade.list(namespace="example-tenant")
    assert api.iter_pages.call_args[0][0].startswith(
        "v1/namespaces/example-tenant/supported-toolchain-versions"
    )
