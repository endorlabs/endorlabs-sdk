"""Tests for workspace summarize."""

from __future__ import annotations

import json
from pathlib import Path

from endorlabs.workflows.estate.export.summarize import (
    format_summary_text,
    summarize_workspace_dir,
)
from endorlabs.workflows.estate.workspace.paths import ensure_workspace_layout, ir_path


def test_summarize_workspace_dir_reads_core_artifacts(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-20260101"
    ensure_workspace_layout(workspace)
    ir_path(workspace, "compile_dependency_graph.json").write_text(
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
    ir_path(workspace, "publisher_rankings.json").write_text(
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

    summary = summarize_workspace_dir(workspace, namespace="tenant")
    assert summary["graph"]["node_count"] == 3
    assert summary["graph"]["isolated_percent"] == 33.3
    assert summary["top_publishers"][0]["rank"] == 1
    text = format_summary_text(summary)
    assert "tenant" in text
    assert "nodes=3" in text
