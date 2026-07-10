"""Tests for compile-graph HTML visualization."""

from __future__ import annotations

import json
from pathlib import Path

from endorlabs.workflows.estate.export.charts.compile_graph_viz import (
    COMPILE_GRAPH_VIZ_SCHEMA,
    export_compile_graph_viz,
    render_compile_graph_viz_html,
)
from endorlabs.workflows.estate.workspace.paths import ensure_workspace_layout, ir_path


def _write_min_workspace(workspace_root: Path) -> None:
    ensure_workspace_layout(workspace_root)
    ir_path(workspace_root, "clustering_graph.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": 0, "name": "https://github.com/acme/importer"},
                    {"id": 1, "name": "https://github.com/acme/producer"},
                ],
                "edges": [
                    {
                        "importer": 0,
                        "producer": 1,
                        "linking_package_name": "maven:com.example:lib",
                        "import_evidence_count": 3,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    ir_path(workspace_root, "producer_rankings.json").write_text(
        json.dumps(
            {
                "total_nodes": 2,
                "producers_with_importers": 1,
                "rankings": [
                    {
                        "name": "https://github.com/acme/producer",
                        "inbound_import_count": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    ir_path(workspace_root, "community_profiles.json").write_text(
        json.dumps(
            {
                "communities": [
                    {
                        "node_count": 2,
                        "edge_count": 1,
                        "dominant_namespaces": [["tenant.child", 2]],
                        "top_linking_packages": [["maven:com.example:lib", 1]],
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
    assert COMPILE_GRAPH_VIZ_SCHEMA in html_doc
    assert 'id="panel-dashboard"' in html_doc
    assert 'id="panel-bipartite"' in html_doc
    assert 'data-tab="dashboard"' in html_doc
    assert 'class="data"' in html_doc
    assert "acme/importer" in html_doc
    assert "tenant.child" in html_doc
    assert "Longest chain" not in html_doc


def test_export_compile_graph_viz_writes_file(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-20260101"
    _write_min_workspace(workspace)
    out = tmp_path / "viz.html"
    export_compile_graph_viz(workspace, out, namespace_label="tenant")
    assert out.is_file()
    assert out.stat().st_size > 500
