"""Unit tests for reachability context call-graph fetch."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

from endorlabs.core.exceptions import NotFoundError
from endorlabs.operations.call_graph import CallGraphDecoded
from endorlabs.workflows.reachability.context import _fetch_decoded_callgraph


def test_fetch_decoded_callgraph_returns_decoded() -> None:
    client = MagicMock()
    decoded = CallGraphDecoded(
        summary={"uuid": "cg-1"},
        callables=[],
        edges=[],
        envelope={},
    )
    client.CallGraphData.decode = Mock(return_value=decoded)

    out = _fetch_decoded_callgraph(
        client,
        package_version_uuid="pv-1",
        namespace="tenant.ns",
    )

    assert out is decoded
    client.CallGraphData.decode.assert_called_once_with(
        "pv-1",
        namespace="tenant.ns",
    )


def test_fetch_decoded_callgraph_not_found_returns_none() -> None:
    client = MagicMock()
    client.CallGraphData.decode = Mock(side_effect=NotFoundError("missing"))

    out = _fetch_decoded_callgraph(
        client,
        package_version_uuid="pv-1",
        namespace="tenant.ns",
    )

    assert out is None
