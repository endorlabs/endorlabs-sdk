"""Unit tests for strict list kwargs on facades."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from endorlabs.facade import ListableFacade
from endorlabs.registry import RESOURCE_REGISTRY


def _project_facade() -> ListableFacade:
    entry = next(e for e in RESOURCE_REGISTRY if e.attr_name == "Project")
    client = Mock()
    return ListableFacade(client, "tenant.ns", entry)


def test_list_unknown_kwarg_raises_type_error() -> None:
    facade = _project_facade()
    with pytest.raises(TypeError, match="Invalid list kwargs"):
        facade.list(filter='meta.name=="x"', unknown_param=True)


def test_list_valid_kwargs_accepted() -> None:
    facade = _project_facade()
    facade._ops = Mock()
    facade._ops.list.return_value = []
    rows = facade.list(filter='meta.name=="x"', mask="meta.name", max_pages=1)
    assert rows == []


def test_list_limit_alias_maps_to_page_size() -> None:
    facade = _project_facade()
    facade._ops = Mock()
    facade._ops.list.return_value = []

    facade.list(limit=10, max_pages=1)

    args, _kwargs = facade._ops.list.call_args
    _ns, list_params, _max_pages = args
    assert list_params is not None
    assert list_params.page_size == 10


def test_list_limit_and_page_size_both_raises() -> None:
    facade = _project_facade()
    with pytest.raises(TypeError, match="limit and page_size"):
        facade.list(limit=10, page_size=5)
