"""Unit tests for graph analytics."""

from __future__ import annotations

import pytest

from endorlabs.workflows.estate.analyze.graph_metrics.analytics import (
    build_package_subgraph,
    compute_graph_metrics,
)


def _toy_graph() -> dict:
    return {
        "namespace": "t",
        "nodes": [
            {"node_id": 0, "name": "a", "in_degree": 0, "out_degree": 1},
            {"node_id": 1, "name": "b", "in_degree": 1, "out_degree": 1},
            {"node_id": 2, "name": "c", "in_degree": 1, "out_degree": 0},
        ],
        "edges": [
            {
                "importer_vertex_id": 0,
                "producer_vertex_id": 1,
                "import_evidence_count": 2,
            },
            {
                "importer_vertex_id": 1,
                "producer_vertex_id": 2,
                "import_evidence_count": 1,
            },
        ],
    }


@pytest.mark.parametrize("extra", ["graph"])
def test_compute_graph_metrics_smoke(extra: str) -> None:
    pytest.importorskip("igraph")
    pytest.importorskip("leidenalg")
    metrics = compute_graph_metrics(_toy_graph(), max_betweenness_nodes=10)
    assert metrics["node_count"] == 3
    assert "centrality" in metrics
    assert metrics["components"]["weakly_connected_count"] >= 1


def test_build_package_subgraph_from_corpus() -> None:
    corpus = [
        {
            "project_uuid": "p1",
            "row": {
                "spec": {
                    "dependency_data": {
                        "package_name": "mvn://com.fasterxml.jackson:jackson-databind",
                        "resolved_version": "2.12.1",
                        "direct": True,
                        "namespace": "oss",
                    }
                }
            },
        }
    ]
    sub = build_package_subgraph(
        corpus, package_name_match="jackson-databind", graph=_toy_graph()
    )
    assert sub["consumer_project_count"] == 1
    assert sub["oss_row_count"] == 1
    assert "2.12.1" in sub["resolved_version_counts"]
