"""Unit tests for compile-graph community detection helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from endorlabs.workflows.estate.analyze.compile_graph.community_detection import (
    CommunityDetectionCheck,
    CommunityDetectionOptions,
    CommunityDetectionValidation,
    build_community_profiles,
    detect_communities,
    load_clustering_graph_input,
)
from endorlabs.workflows.estate.workspace.paths import ensure_workspace_layout, ir_path


def test_community_detection_validation_to_dict() -> None:
    validation = CommunityDetectionValidation(
        ok=True,
        checks=[CommunityDetectionCheck("membership_complete", True, "ok")],
        generated_at="2026-01-01T00:00:00+00:00",
    )
    payload = validation.to_dict()
    assert payload["phase"] == "detect_communities"
    assert payload["checks"][0]["name"] == "membership_complete"


def test_build_community_profiles_aggregates_namespaces_and_packages() -> None:
    import_graph = {
        "namespace": "tenant.ns",
        "nodes": [
            {
                "node_id": 0,
                "project_uuid": "a",
                "namespace": "tenant.ns",
                "namespaces": ["tenant.ns"],
                "tags": ["team-a"],
            },
            {
                "node_id": 1,
                "project_uuid": "b",
                "namespace": "tenant.child",
                "tags": ["team-b"],
            },
        ],
        "edges": [
            {
                "importer_vertex_id": 0,
                "producer_vertex_id": 1,
                "linking_package_name": "mvn://lib",
            }
        ],
    }
    communities = [{"community_id": 0, "node_ids": [0, 1]}]
    profiles = build_community_profiles(import_graph, communities)
    row = profiles["communities"][0]
    assert row["node_count"] == 2
    assert row["edge_count"] == 1
    assert row["top_linking_packages"][0][0] == "mvn://lib"
    assert row["hub_importer_vertex_ids"] == [1]


def test_load_clustering_graph_input_prefers_clustering_json(tmp_path: Path) -> None:
    ensure_workspace_layout(tmp_path)
    ir_path(tmp_path, "clustering_graph.json").write_text(
        json.dumps(
            {
                "namespace": "tenant.ns",
                "nodes": [{"id": 0, "name": "proj-a"}],
                "edges": [
                    {
                        "importer": 0,
                        "producer": 1,
                        "linking_package_name": "mvn://x",
                        "import_evidence_count": 2,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    ir_path(tmp_path, "compile_dependency_graph_enriched.json").write_text(
        json.dumps(
            {
                "nodes": [{"node_id": 0, "project_uuid": "proj-a", "tags": ["t"]}],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )
    loaded = load_clustering_graph_input(tmp_path)
    assert loaded["namespace"] == "tenant.ns"
    assert loaded["nodes"][0]["tags"] == ["t"]
    assert loaded["edges"][0]["import_evidence_count"] == 2


def test_load_clustering_graph_input_falls_back_to_compile_graph(
    tmp_path: Path,
) -> None:
    ensure_workspace_layout(tmp_path)
    ir_path(tmp_path, "compile_dependency_graph.json").write_text(
        json.dumps({"namespace": "tenant.ns", "nodes": [], "edges": []}),
        encoding="utf-8",
    )
    loaded = load_clustering_graph_input(tmp_path)
    assert loaded["namespace"] == "tenant.ns"


def test_detect_communities_empty_graph() -> None:
    payload, validation, profiles = detect_communities({"nodes": [], "edges": []})
    assert not validation.ok
    assert payload == {}
    assert profiles == {}


def test_detect_communities_import_error_when_graph_extra_missing() -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args, **kwargs):  # noqa: ANN002, ANN003
        if name in {"igraph", "leidenalg"}:
            raise ImportError("graph extra not installed")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        payload, validation, profiles = detect_communities(
            {"nodes": [{"node_id": 0}], "edges": []}
        )
    assert not validation.ok
    assert payload == {}
    assert profiles == {}
    assert validation.checks[0].name == "igraph_leidenalg_installed"


def test_detect_communities_component_min_size_rejects_small_graph() -> None:
    pytest.importorskip("igraph")
    pytest.importorskip("leidenalg")
    import_graph = {
        "nodes": [{"node_id": 0, "project_uuid": "solo"}],
        "edges": [],
    }
    payload, validation, _ = detect_communities(
        import_graph,
        options=CommunityDetectionOptions(component_min_size=5),
    )
    assert not validation.ok
    assert payload == {}


def test_load_clustering_graph_input_legacy_session_layout(tmp_path: Path) -> None:
    (tmp_path / "compile_dependency_graph.json").write_text(
        json.dumps(
            {
                "namespace": "tenant.ns",
                "nodes": [{"node_id": 0}],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )
    loaded = load_clustering_graph_input(
        tmp_path, use_intermediate_representation=False
    )
    assert loaded["namespace"] == "tenant.ns"


def test_detect_communities_rber_partition_when_vertex_weights_set() -> None:
    pytest.importorskip("igraph")
    pytest.importorskip("leidenalg")
    import_graph = {
        "namespace": "tenant.ns",
        "nodes": [
            {"node_id": 0, "project_uuid": "a", "in_degree": 0},
            {"node_id": 1, "project_uuid": "b", "in_degree": 2},
        ],
        "edges": [
            {
                "importer_vertex_id": 0,
                "producer_vertex_id": 1,
                "linking_package_name": "mvn://x",
                "import_evidence_count": 3,
            }
        ],
    }
    payload, validation, _ = detect_communities(
        import_graph,
        options=CommunityDetectionOptions(
            edge_weight_source="import_evidence_count",
            vertex_weight_source="inbound_import_count",
        ),
    )
    assert validation.ok
    assert payload["method"] == "potts_leiden"
