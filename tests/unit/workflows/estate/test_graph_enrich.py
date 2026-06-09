"""Unit tests for graph enrichment."""

from __future__ import annotations

from typing import Any

from endorlabs.workflows.estate.analyze.compile_graph.enrich import enrich_graph


def _minimal_graph() -> dict[str, Any]:
    return {
        "schema": "endor.compile_dependency_graph.v1",
        "namespace": "tenant.ns",
        "nodes": [
            {
                "node_id": 0,
                "project_uuid": "consumer-1",
                "project_uuids": ["consumer-1"],
                "name": "https://github.com/a/repo",
                "namespace": "tenant.ns",
                "published_packages": [{"package_name": "mvn://com.acme:lib"}],
                "in_degree": 0,
                "out_degree": 1,
            },
            {
                "node_id": 1,
                "project_uuid": "publisher-1",
                "project_uuids": ["publisher-1"],
                "name": "https://github.com/b/lib",
                "namespace": "tenant.ns",
                "published_packages": [],
                "in_degree": 1,
                "out_degree": 0,
            },
        ],
        "edges": [
            {
                "source_id": 0,
                "target_id": 1,
                "anchor_package_name": "mvn://com.acme:lib",
            }
        ],
    }


def test_enrich_graph_adds_corpus_stats() -> None:
    graph = _minimal_graph()
    discover = [
        {
            "uuid": "consumer-1",
            "tags": ["team-a"],
            "namespace": "tenant.ns",
            "namespaces": ["tenant.ns"],
        }
    ]
    corpus = [
        {
            "project_uuid": "consumer-1",
            "dm_uuid": "dm-1",
            "row": {
                "uuid": "dm-1",
                "spec": {
                    "dependency_data": {
                        "package_name": "mvn://com.acme:lib",
                        "resolved_version": "1.0",
                        "direct": True,
                        "scope": "DEPENDENCY_SCOPE_BUILD",
                        "namespace": "oss",
                    }
                },
            },
        }
    ]
    result = enrich_graph(graph, discover_rows=discover, corpus_records=corpus)
    node0 = result.enriched["nodes"][0]
    assert node0["corpus_dependency_count"] == 1
    assert node0["corpus_direct_count"] == 1
    assert "team-a" in node0["tags"]
    edge = result.enriched["edges"][0]
    assert edge["consumer_row_count"] == 1
    assert "1.0" in edge["resolved_versions"]
    assert result.leiden_input["node_count"] == 2


def test_enrich_graph_risk_metadata() -> None:
    graph = _minimal_graph()
    result = enrich_graph(
        graph,
        discover_rows=[],
        corpus_records=[],
        risk_by_package={
            "mvn://com.acme:lib": {
                "risk_score": 12.0,
                "findings_critical": 2,
                "findings_high": 1,
                "findings_total": 3,
                "version_cardinality": 4,
            }
        },
    )
    node0 = result.enriched["nodes"][0]
    assert node0["risk_score_max"] == 12.0
    assert node0["findings_critical_max"] == 2
    assert node0["findings_high_max"] == 1
