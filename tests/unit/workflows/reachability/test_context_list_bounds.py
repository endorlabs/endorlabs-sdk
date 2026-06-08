"""Unit tests for reachability context list bounds."""

from __future__ import annotations

from unittest.mock import Mock

from endorlabs.workflows.reachability.context import _list_callgraph_for_parent


def test_list_callgraph_unlimited_uses_get_all() -> None:
    api = Mock()
    api.get_all.return_value = iter([{"uuid": "cg-1"}])

    objs, truncated = _list_callgraph_for_parent(
        api,
        namespace="tenant.ns",
        parent_uuid="pv-1",
        page_size=200,
        max_pages=0,
    )

    assert objs == [{"uuid": "cg-1"}]
    assert truncated is False
    assert api.get_all.call_args.kwargs["max_pages"] is None


def test_list_callgraph_truncated_at_capacity() -> None:
    api = Mock()
    api.get_all.return_value = iter([{"uuid": f"cg-{i}"} for i in range(10)])

    _, truncated = _list_callgraph_for_parent(
        api,
        namespace="tenant.ns",
        parent_uuid="pv-1",
        page_size=10,
        max_pages=1,
    )

    assert truncated is True
