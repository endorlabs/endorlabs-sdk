"""Unit tests for direct-edge call graph search."""

from __future__ import annotations

import json
from pathlib import Path

from endorlabs.workflows.callgraph.search import search_decoded_call_graph

_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "fixtures"
    / "callgraph"
    / "minimal_wrapper_chain.json"
)


def test_search_finds_inner_wrapper_edge() -> None:
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    result = search_decoded_call_graph(
        data["callables"],
        data["edges"],
        node_patterns=[],
        source_patterns=["_request_with_retry"],
        target_patterns=["Client.request"],
    )
    assert result["edge_hits_total"] == 1
    assert "Client.request" in result["edge_hits"][0]["target_uri"]
