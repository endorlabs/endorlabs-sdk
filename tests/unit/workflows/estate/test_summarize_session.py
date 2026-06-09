"""Tests for workspace summarize."""

from __future__ import annotations

import json
from pathlib import Path

from endorlabs.workflows.estate.export.summarize import (
    format_summary_text,
    summarize_workspace_dir,
)
from endorlabs.workflows.estate.export.summarize import (
    main as summarize_main,
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
    ir_path(workspace, "producer_rankings.json").write_text(
        json.dumps(
            {
                "producers_with_importers": 1,
                "rankings": [
                    {
                        "rank": 1,
                        "name": "mvn://com.example:lib",
                        "importer_count": 2,
                        "inbound_import_count": 2,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    summary = summarize_workspace_dir(workspace, namespace="tenant")
    assert summary["graph"]["node_count"] == 3
    assert summary["graph"]["isolated_percent"] == 33.3
    assert summary["top_producers"][0]["rank"] == 1
    text = format_summary_text(summary)
    assert "tenant" in text
    assert "nodes=3" in text


def test_summarize_includes_community_detection_and_metrics(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-20260101"
    ensure_workspace_layout(workspace)
    ir_path(workspace, "compile_dependency_graph.json").write_text(
        json.dumps(
            {"node_count": 2, "edge_count": 1, "isolated_count": 0, "nodes": []}
        ),
        encoding="utf-8",
    )
    ir_path(workspace, "community_detection.json").write_text(
        json.dumps(
            {
                "method": "modularity_leiden",
                "resolution": 1.0,
                "edge_weight_source": "none",
                "vertex_weight_source": "none",
                "membership": {"0": 0, "1": 0},
                "community_count": 1,
            }
        ),
        encoding="utf-8",
    )
    ir_path(workspace, "graph_metrics.json").write_text(
        json.dumps(
            {
                "components": {
                    "weakly_connected_count": 1,
                    "weakly_connected_sizes": [2],
                },
                "scc": {"has_cycles": False},
                "k_core": {"max_k": 1},
            }
        ),
        encoding="utf-8",
    )

    summary = summarize_workspace_dir(workspace, namespace="tenant")
    assert summary["community_detection"]["method"] == "modularity_leiden"
    assert summary["metrics"]["weakly_connected_components"] == 1
    text = format_summary_text(summary)
    assert "groups:" in text
    assert "metrics:" in text


def test_summarize_main_json_output(tmp_path: Path, capsys) -> None:
    workspace = tmp_path / "tenant-20260101"
    ensure_workspace_layout(workspace)
    ir_path(workspace, "compile_dependency_graph.json").write_text(
        json.dumps(
            {"node_count": 1, "edge_count": 0, "isolated_count": 0, "nodes": []}
        ),
        encoding="utf-8",
    )
    rc = summarize_main(
        ["--namespace", "tenant", "--workspace", str(workspace), "--json"]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["graph"]["node_count"] == 1


def test_summarize_main_reports_missing_graph(tmp_path: Path, capsys) -> None:
    workspace = tmp_path / "empty"
    ensure_workspace_layout(workspace)
    rc = summarize_main(
        ["--namespace", "tenant", "--workspace", str(workspace), "--json"]
    )
    assert rc == 1
    assert "compile_dependency_graph.json" in capsys.readouterr().err
