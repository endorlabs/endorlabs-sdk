"""Tests for BaseResourceOperations.get traverse fallback namespace scoping."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from endorlabs.core.exceptions import NotFoundError
from endorlabs.core.types import ListParameters
from endorlabs.operations import BaseResourceOperations
from endorlabs.resources.base import BaseMeta, BaseResource, TenantMeta


class _Project(BaseResource):
    pass


def _http_404() -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://api.example/v1/namespaces/t/projects/u")
    response = httpx.Response(404, request=request)
    return httpx.HTTPStatusError("not found", request=request, response=response)


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client.get = MagicMock(side_effect=_http_404())
    client.map_http_error_to_exception = MagicMock()
    return client


def test_get_fallback_returns_descendant_namespace_match(
    mock_client: MagicMock,
) -> None:
    """Traverse fallback may return a row in a child namespace under the request path."""
    child = _Project(
        uuid="proj-1",
        meta=BaseMeta(),
        tenant_meta=TenantMeta(namespace="tenant.root.team"),
    )
    ops = BaseResourceOperations(mock_client, "projects", _Project)
    ops.list = MagicMock(return_value=[child])

    result = ops.get("tenant.root", "proj-1")

    assert result is child
    ops.list.assert_called_once()
    list_params = ops.list.call_args[0][1]
    assert isinstance(list_params, ListParameters)
    assert list_params.traverse is True


def test_get_fallback_rejects_sibling_namespace_match(
    mock_client: MagicMock,
) -> None:
    """Traverse fallback must not return a row outside the requested namespace tree."""
    sibling = _Project(
        uuid="proj-1",
        meta=BaseMeta(),
        tenant_meta=TenantMeta(namespace="tenant.other"),
    )
    ops = BaseResourceOperations(mock_client, "projects", _Project)
    ops.list = MagicMock(return_value=[sibling])

    with pytest.raises(NotFoundError, match="not found"):
        ops.get("tenant.root.team", "proj-1")


def test_get_fallback_prefers_in_tree_row_when_multiple_returned(
    mock_client: MagicMock,
) -> None:
    """When traverse returns multiple rows, pick the first in the namespace tree."""
    out_of_tree = _Project(
        uuid="proj-1",
        meta=BaseMeta(),
        tenant_meta=TenantMeta(namespace="tenant.other"),
    )
    in_tree = _Project(
        uuid="proj-1",
        meta=BaseMeta(),
        tenant_meta=TenantMeta(namespace="tenant.root.team"),
    )
    ops = BaseResourceOperations(mock_client, "projects", _Project)
    ops.list = MagicMock(return_value=[out_of_tree, in_tree])

    result = ops.get("tenant.root", "proj-1")

    assert result is in_tree
