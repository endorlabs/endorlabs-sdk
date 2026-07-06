"""Tests for unified estate dashboard HTML."""

from __future__ import annotations

import json
from pathlib import Path

from endorlabs.workflows.estate.export.charts.estate_dashboard import (
    export_estate_dashboard,
    render_estate_dashboard_html,
)
from endorlabs.workflows.estate.workspace.paths import ensure_workspace_layout, ir_path


def _write_min_workspace(workspace_root: Path) -> None:
    ensure_workspace_layout(workspace_root)
    ir_path(workspace_root, "risk_cardinality.json").write_text(
        json.dumps(
            {
                "packages": [
                    {
                        "package_name": "mvn://com.example:lib",
                        "risk_score": 100,
                        "findings_critical": 1,
                        "findings_high": 2,
                        "version_cardinality": 2,
                        "versions": [
                            {
                                "version": "1.0",
                                "usage_count": 5,
                                "risk_score": 100,
                                "findings_critical": 1,
                                "findings_high": 2,
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    ir_path(workspace_root, "clustering_graph.json").write_text(
        json.dumps(
            {
                "nodes": [{"id": 0, "name": "https://github.com/acme/a"}],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )
    ir_path(workspace_root, "producer_rankings.json").write_text(
        json.dumps({"total_nodes": 1, "producers_with_importers": 0, "rankings": []}),
        encoding="utf-8",
    )


def test_estate_dashboard_includes_risk_and_graph_tabs(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-20260101"
    _write_min_workspace(workspace)
    html_doc = render_estate_dashboard_html(workspace, namespace_label="tenant")
    assert "Risk families" in html_doc
    assert "Internal dependencies" in html_doc
    assert "mvn://com.example:lib" in html_doc
    assert "Longest chain" not in html_doc


def test_estate_dashboard_includes_online_query_tiles(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-20260101"
    _write_min_workspace(workspace)
    ir_path(workspace, "online_dashboard_counts.json").write_text(
        json.dumps(
            {
                "schema": "endor.online_dashboard_counts.v1",
                "archetype": "managed_platform",
                "totals": {
                    "pv": 42,
                    "dm": 7,
                    "findings": {
                        "VULNERABILITY": 3,
                        "SECRETS": 1,
                        "MALWARE": 0,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    html_doc = render_estate_dashboard_html(workspace, namespace_label="tenant")
    assert "PV (Query)" in html_doc
    assert "42" in html_doc
    assert "managed_platform" in html_doc


def test_export_estate_dashboard_writes_viz(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-20260101"
    _write_min_workspace(workspace)
    out = export_estate_dashboard(workspace, namespace_label="tenant")
    assert out.name == "estate_dashboard.html"
    assert out.parent.name == "viz"
    assert out.stat().st_size > 300
