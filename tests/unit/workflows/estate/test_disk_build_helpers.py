"""Unit tests for workspace compile-graph disk build helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from endorlabs.workflows.estate.analyze.compile_graph import disk_build
from endorlabs.workflows.estate.contracts import (
    RESOURCE_PACKAGE_VERSION,
    RESOURCE_PROJECT,
)
from endorlabs.workflows.estate.workspace.paths import (
    ensure_workspace_layout,
    ir_path,
    resource_path,
)


def test_discover_rows_from_projects_maps_tags_and_namespace() -> None:
    rows = disk_build._discover_rows_from_projects(
        [
            {
                "uuid": "p1",
                "meta": {"name": "https://github.com/a", "tags": ["team"]},
                "tenant_meta": {"namespace": "tenant.child"},
            }
        ],
        "tenant.root",
    )
    assert rows[0]["uuid"] == "p1"
    assert rows[0]["tags"] == ["team"]
    assert rows[0]["namespace"] == "tenant.child"


def test_load_published_by_project_reads_jsonl(tmp_path: Path) -> None:
    ensure_workspace_layout(tmp_path)
    path = resource_path(tmp_path, RESOURCE_PACKAGE_VERSION)
    path.write_text(
        json.dumps(
            {
                "project_uuid": "p1",
                "package_name": "pypi://django",
                "package_version": "4.2",
                "package_version_name": "pypi://django@4.2",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    published = disk_build._load_published_by_project(tmp_path)
    assert published["p1"][0]["package_name"] == "pypi://django"


def test_build_producer_indices_from_published_rows() -> None:
    produced_by, produced_name = disk_build._build_producer_indices(
        {
            "p1": [
                {
                    "package_name": "pypi://django",
                    "package_version": "4.2",
                    "package_version_name": "pypi://django@4.2",
                }
            ]
        }
    )
    assert "p1" in produced_name["pypi://django"]
    assert "p1" in produced_by[("pypi://django", "4.2")]


def test_object_to_spec_dict_extracts_nested_spec() -> None:
    assert disk_build._object_to_spec_dict({"row": {"spec": {"a": 1}}}) == {"a": 1}
    assert disk_build._object_to_spec_dict({}) == {}


def test_write_compile_graph_ir_writes_artifacts(tmp_path: Path) -> None:
    ensure_workspace_layout(tmp_path)
    fake_graph = {"namespace": "tenant.ns", "nodes": [], "edges": []}
    fake_rankings = {"rankings": []}
    with patch.object(
        disk_build,
        "build_compile_graph_from_workspace",
        return_value=(fake_graph, fake_rankings),
    ):
        graph = disk_build.write_compile_graph_ir(tmp_path, namespace="tenant.ns")
    assert graph == fake_graph
    assert (
        tmp_path / "intermediate-representation" / "compile_dependency_graph.json"
    ).is_file()


def test_run_graph_pipeline_from_workspace_writes_detection(tmp_path: Path) -> None:
    ensure_workspace_layout(tmp_path)
    enriched = {"namespace": "tenant.ns", "nodes": [], "edges": []}
    with (
        patch.object(disk_build, "write_compile_graph_ir"),
        patch.object(disk_build, "run_enrich_graph_phase"),
        patch.object(disk_build, "run_graph_analytics_phase"),
        patch.object(
            disk_build,
            "detect_communities",
            return_value=({"ok": True}, object(), {"communities": []}),
        ),
    ):
        ir_path(tmp_path, "compile_dependency_graph_enriched.json").write_text(
            json.dumps(enriched),
            encoding="utf-8",
        )
        disk_build.run_graph_pipeline_from_workspace(tmp_path, namespace="tenant.ns")
    assert ir_path(tmp_path, "community_detection.json").is_file()
    assert ir_path(tmp_path, "community_profiles.json").is_file()


def test_build_compile_graph_from_workspace_minimal(tmp_path: Path) -> None:
    ensure_workspace_layout(tmp_path)
    resource_path(tmp_path, RESOURCE_PROJECT).write_text(
        json.dumps(
            {
                "uuid": "p1",
                "meta": {"name": "https://github.com/a"},
                "tenant_meta": {"namespace": "tenant.ns"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    graph, rankings = disk_build.build_compile_graph_from_workspace(
        tmp_path, namespace="tenant.ns"
    )
    assert graph["namespace"] == "tenant.ns"
    assert "rankings" in rankings
