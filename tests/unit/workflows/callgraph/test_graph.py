"""Unit tests for call-graph graph utilities."""

from __future__ import annotations

from endorlabs.workflows.callgraph.graph import (
    build_out_adjacency,
    build_uri_index,
    matches_all_patterns,
    resolve_method_ids_by_patterns,
)


def test_matches_all_patterns_case_insensitive() -> None:
    assert matches_all_patterns("FooBar/Baz", ["foo", "baz"]) is True
    assert matches_all_patterns("FooBar", ["missing"]) is False
    assert matches_all_patterns("anything", []) is True


def test_build_uri_index_and_adjacency() -> None:
    callables = [{"method_id": 1, "uri": "a"}, {"method_id": 2, "uri": "b"}]
    edges = [{"source_id": 1, "target_id": 2}]
    assert build_uri_index(callables) == {1: "a", 2: "b"}
    assert build_out_adjacency(edges) == {1: [2]}


def test_resolve_method_ids_by_patterns() -> None:
    callables = [
        {"method_id": 10, "uri": "python://myapp/api_client/APIClient.get()"},
        {"method_id": 11, "uri": "python://httpx/_client/Client.request()"},
    ]
    ids = resolve_method_ids_by_patterns(callables, ["APIClient", "get"])
    assert ids == [10]
