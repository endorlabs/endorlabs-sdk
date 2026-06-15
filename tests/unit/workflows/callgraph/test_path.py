"""Unit tests for call-graph BFS path search."""

from __future__ import annotations

import json
from pathlib import Path

from endorlabs.workflows.callgraph.path import find_call_graph_path
from endorlabs.workflows.callgraph.search import search_decoded_call_graph

_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "fixtures"
    / "callgraph"
    / "minimal_wrapper_chain.json"
)


def _load_fixture() -> tuple[list, list]:
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return data["callables"], data["edges"]


def test_direct_edge_get_to_httpx_is_zero() -> None:
    callables, edges = _load_fixture()
    result = search_decoded_call_graph(
        callables,
        edges,
        node_patterns=[],
        source_patterns=["APIClient", "get"],
        target_patterns=["httpx"],
    )
    assert result["edge_hits_total"] == 0


def test_bfs_finds_wrapper_chain_to_client_request() -> None:
    callables, edges = _load_fixture()
    result = find_call_graph_path(
        callables,
        edges,
        from_patterns=["APIClient", "get"],
        to_patterns=["Client.request"],
        max_depth=6,
    )
    assert result["path_found"] is True
    assert result["paths_total"] >= 1
    hops = result["paths"][0]
    assert len(hops) == 4
    assert "APIClient.get" in hops[0]["uri"]
    assert "Client.request" in hops[-1]["uri"]


def test_bfs_respects_max_depth() -> None:
    callables, edges = _load_fixture()
    result = find_call_graph_path(
        callables,
        edges,
        from_patterns=["APIClient", "get"],
        to_patterns=["Client.request"],
        max_depth=1,
    )
    assert result["path_found"] is False


def test_bfs_empty_patterns_returns_no_path() -> None:
    callables, edges = _load_fixture()
    result = find_call_graph_path(
        callables,
        edges,
        from_patterns=[],
        to_patterns=["Client.request"],
    )
    assert result["path_found"] is False
    assert result["source_ids"] == []
