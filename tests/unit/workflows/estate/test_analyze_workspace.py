"""Tests for disk-first analyze_workspace orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from endorlabs.workflows.estate.analyze.workspace import analyze_workspace
from endorlabs.workflows.estate.contracts import RESOURCE_DEPENDENCY_METADATA
from endorlabs.workflows.estate.workspace.collect_manifest import (
    CollectManifest,
    finalize_resource,
    save_collect_manifest,
)
from endorlabs.workflows.estate.workspace.paths import (
    ensure_workspace_layout,
    ir_path,
    resource_path,
)


def _write_dm_workspace(workspace: Path) -> None:
    ensure_workspace_layout(workspace)
    dm_path = resource_path(workspace, RESOURCE_DEPENDENCY_METADATA)
    dm_path.write_text(
        json.dumps(
            {
                "project_uuid": "p1",
                "row": {
                    "spec": {
                        "dependency_data": {
                            "package_name": "pypi://django",
                            "resolved_version": "4.2",
                        }
                    }
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = CollectManifest.new("tenant.example")
    finalize_resource(
        manifest,
        RESOURCE_DEPENDENCY_METADATA,
        status="complete",
        line_count=1,
    )
    save_collect_manifest(workspace, manifest)


def test_analyze_workspace_cardinality_step(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-20260101"
    _write_dm_workspace(workspace)
    result = analyze_workspace(
        workspace,
        namespace="tenant.example",
        only=("cardinality",),
        skip_validate=True,
    )
    assert result.steps["cardinality"].endswith("packages")
    payload = json.loads(
        ir_path(workspace, "version_cardinality.json").read_text(encoding="utf-8")
    )
    assert payload["package_count"] >= 1


def test_analyze_workspace_viz_step_uses_dashboard_export(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-20260101"
    ensure_workspace_layout(workspace)
    ir_path(workspace, "risk_cardinality.json").write_text(
        json.dumps({"packages": []}),
        encoding="utf-8",
    )
    ir_path(workspace, "clustering_graph.json").write_text(
        json.dumps({"nodes": [], "edges": []}),
        encoding="utf-8",
    )
    ir_path(workspace, "producer_rankings.json").write_text(
        json.dumps({"total_nodes": 0, "producers_with_importers": 0, "rankings": []}),
        encoding="utf-8",
    )
    with patch(
        "endorlabs.workflows.estate.analyze.workspace.export_estate_dashboard",
        return_value=workspace / "viz" / "estate_dashboard.html",
    ) as mock_export:
        result = analyze_workspace(
            workspace,
            namespace="tenant.example",
            only=("viz",),
            skip_validate=True,
        )
    mock_export.assert_called_once()
    assert "estate_dashboard.html" in result.steps["viz"]


def test_analyze_workspace_risk_step(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-20260101"
    ensure_workspace_layout(workspace)
    fake_risk = MagicMock(message="risk ok")
    with patch(
        "endorlabs.workflows.estate.analyze.workspace.analyze_risk_cardinality_from_workspace",
        return_value=fake_risk,
    ) as mock_risk:
        result = analyze_workspace(
            workspace,
            namespace="tenant.example",
            only=("risk",),
            skip_validate=True,
        )
    mock_risk.assert_called_once()
    assert result.steps["risk"] == "risk ok"
