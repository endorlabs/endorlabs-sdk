"""Tests for compile-graph HTML visualization."""

from __future__ import annotations

import json
from pathlib import Path

from endorlabs.workflows.estate.export.charts.compile_graph_viz import (
    export_compile_graph_viz,
    render_compile_graph_viz_html,
)
from endorlabs.workflows.estate.workspace.paths import ensure_workspace_layout, ir_path


def _write_min_workspace(workspace_root: Path) -> None:
    ensure_workspace_layout(workspace_root)
    ir_path(workspace_root, "leiden_input.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": 0, "name": "https://github.com/acme/consumer"},
                    {"id": 1, "name": "https://github.com/acme/publisher"},
                ],
                "edges": [
                    {
                        "source": 0,
                        "target": 1,
                        "anchor_package_name": "maven:com.example:lib",
                        "weight": 3,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    ir_path(workspace_root, "publisher_rankings.json").write_text(
        json.dumps(
            {
                "total_nodes": 2,
                "publishers_with_consumers": 1,
                "rankings": [
                    {
                        "name": "https://github.com/acme/publisher",
                        "inbound_edge_count": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    ir_path(workspace_root, "community_summary.json").write_text(
        json.dumps(
            {
                "communities": [
                    {
                        "node_count": 2,
                        "edge_count": 1,
                        "dominant_namespaces": [["tenant.child", 2]],
                        "top_anchor_packages": [["maven:com.example:lib", 1]],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_render_compile_graph_viz_html(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-20260101"
    _write_min_workspace(workspace)
    html_doc = render_compile_graph_viz_html(workspace, namespace_label="tenant")
    assert "Compile-dependency graph" in html_doc
    assert "Largest Leiden communities" in html_doc
    assert "acme/consumer" in html_doc
    assert "Longest chain" not in html_doc


def test_export_compile_graph_viz_writes_file(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-20260101"
    _write_min_workspace(workspace)
    out = tmp_path / "viz.html"
    export_compile_graph_viz(workspace, out, namespace_label="tenant")
    assert out.is_file()
    assert out.stat().st_size > 500
