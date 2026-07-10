"""Tests for tools.callgraph_artifacts summarization."""

from __future__ import annotations

from endorlabs.tools.callgraph_artifacts import summarize_call_graph


def test_summarize_call_graph_basic() -> None:
    summary = summarize_call_graph(
        {
            "uuid": "cg-1",
            "meta": {"name": "pkg", "parent_uuid": "pv-1"},
            "spec": {"zstd_bytes": "abc"},
        }
    )
    assert summary["uuid"] == "cg-1"
    assert summary["name"] == "pkg"
    assert summary["call_graph_format"] == "zstd_bytes (binary)"
    assert summary["zstd_bytes_length"] == 3
