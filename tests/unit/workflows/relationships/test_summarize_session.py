"""Tests for graph session summarize CLI."""

from __future__ import annotations

import json
from pathlib import Path

from endorlabs.workflows.relationships.summarize_session import (
    format_summary_text,
    summarize_session_dir,
)


def test_summarize_session_dir_reads_core_artifacts(tmp_path: Path) -> None:
    session = tmp_path / "tenant"
    session.mkdir()
    (session / "compile_dependency_graph.json").write_text(
        json.dumps(
            {
                "node_count": 3,
                "edge_count": 1,
                "isolated_count": 1,
                "nodes": [
                    {"node_id": 0, "isolated": False},
                    {"node_id": 1, "isolated": False},
                    {"node_id": 2, "isolated": True},
                ],
            }
        ),
        encoding="utf-8",
    )
    (session / "publisher_rankings.json").write_text(
        json.dumps(
            {
                "publishers_with_consumers": 1,
                "rankings": [
                    {
                        "rank": 1,
                        "name": "mvn://com.example:lib",
                        "consumer_count": 2,
                        "inbound_edge_count": 2,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (session / "phase_build_graph_validation.json").write_text(
        json.dumps({"ok": True}),
        encoding="utf-8",
    )

    summary = summarize_session_dir(session, namespace="tenant")
    assert summary["graph"]["node_count"] == 3
    assert summary["graph"]["isolated_percent"] == 33.3
    assert summary["top_publishers"][0]["rank"] == 1
    assert summary["phase_validation"]["build_graph"] is True
    text = format_summary_text(summary)
    assert "tenant" in text
    assert "nodes=3" in text
