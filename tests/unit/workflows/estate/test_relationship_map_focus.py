"""Tests for focus-producer filtering in relationship map runs."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from endorlabs.workflows.estate.analyze.project_map import run as rel_run


def _project(uuid: str, name: str, namespace: str) -> SimpleNamespace:
    return SimpleNamespace(
        uuid=uuid,
        meta=SimpleNamespace(name=name),
        tenant_meta=SimpleNamespace(namespace=namespace),
    )


def _package_version(project_uuid: str, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        spec=SimpleNamespace(project_uuid=project_uuid),
        meta=SimpleNamespace(name=name),
    )


def _dependency_row(consumer_uuid: str) -> SimpleNamespace:
    return SimpleNamespace(
        model_dump=lambda **_: {
            "spec": {
                "importer_data": {"project_uuid": consumer_uuid},
                "dependency_data": {
                    "package_name": "npm://internal-lib",
                    "resolved_version": "1.0.0",
                    "direct": True,
                    "public": False,
                },
            }
        }
    )


def test_focus_producer_filters_edges_and_producer_index(tmp_path: Path) -> None:
    producer = "producer-uuid"
    consumer = "consumer-uuid"
    projects = [
        _project(producer, "https://github.com/o/producer.git", "tenant.ns"),
        _project(consumer, "https://github.com/o/consumer.git", "tenant.ns"),
    ]
    pvs = [
        _package_version(producer, "npm://internal-lib@1.0.0"),
        _package_version(consumer, "npm://consumer-app@2.0.0"),
    ]

    fake_client = Mock()
    fake_client.Project.list.return_value = projects
    fake_client.PackageVersion.list.return_value = pvs
    fake_client.DependencyMetadata.list.return_value = [_dependency_row(consumer)]

    result = rel_run.run_project_relationship_map(
        fake_client,
        namespace="tenant.ns",
        output_dir=tmp_path,
        max_pages=1,
        page_size=100,
        dep_metadata_max_pages=1,
        max_workers=1,
        focus_producer_project_uuid=producer,
    )

    assert result.stats["focus_producer_project_uuid"] == producer
    assert result.stats["direct_project_edge_count"] == 1
    graph_path = tmp_path / "project_relationship_graph.json"
    assert graph_path.is_file()
    assert consumer in graph_path.read_text(encoding="utf-8")


def test_focus_producer_excludes_unrelated_producer_edges(tmp_path: Path) -> None:
    producer = "producer-uuid"
    other_producer = "other-producer-uuid"
    consumer = "consumer-uuid"
    projects = [
        _project(producer, "https://github.com/o/producer.git", "tenant.ns"),
        _project(other_producer, "https://github.com/o/other.git", "tenant.ns"),
        _project(consumer, "https://github.com/o/consumer.git", "tenant.ns"),
    ]
    pvs = [
        _package_version(producer, "npm://internal-lib@1.0.0"),
        _package_version(other_producer, "npm://other-lib@1.0.0"),
    ]

    fake_client = Mock()
    fake_client.Project.list.return_value = projects
    fake_client.PackageVersion.list.return_value = pvs
    fake_client.DependencyMetadata.list.return_value = [_dependency_row(consumer)]

    result = rel_run.run_project_relationship_map(
        fake_client,
        namespace="tenant.ns",
        output_dir=tmp_path,
        max_pages=1,
        page_size=100,
        dep_metadata_max_pages=1,
        max_workers=1,
        focus_producer_project_uuid=producer,
    )

    assert result.stats["direct_project_edge_count"] == 1
