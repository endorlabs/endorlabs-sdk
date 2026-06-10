"""Tests for relationships.map CLI flow."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from endorlabs.workflows.estate.analyze.project_map import map as rel_map
from endorlabs.workflows.estate.analyze.project_map import run as rel_run
from endorlabs.workflows.estate.analyze.project_map.run import RelationshipMapResult


def _project(uuid: str, name: str, namespace: str) -> SimpleNamespace:
    return SimpleNamespace(
        uuid=uuid,
        meta=SimpleNamespace(name=name),
        tenant_meta=SimpleNamespace(namespace=namespace),
    )


def _package_version(project_uuid: str, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        spec=SimpleNamespace(project_uuid=project_uuid), meta=SimpleNamespace(name=name)
    )


def test_object_to_spec_dict_supports_model_dump_and_raw() -> None:
    dumped = SimpleNamespace(model_dump=lambda **_: {"spec": {"a": 1}})
    assert rel_run._object_to_spec_dict(dumped) == {"a": 1}
    assert rel_run._object_to_spec_dict({"spec": {"b": 2}}) == {"b": 2}
    assert rel_run._object_to_spec_dict("bad") == {}


def test_main_writes_graph_artifacts_and_closes_client() -> None:
    fake_client = Mock()
    fake_result = RelationshipMapResult(
        graph_path=Path(".tmp/project_relationship_graph.json"),
        paths_path=Path(".tmp/project_relationship_paths.json"),
        stats_path=Path(".tmp/project_relationship_stats.json"),
        stats={"direct_project_edge_count": 1},
    )

    with (
        patch(
            "endorlabs.workflows.estate.analyze.project_map.map.endorlabs.Client",
            return_value=fake_client,
        ),
        patch(
            "endorlabs.workflows.estate.analyze.project_map.map.run_project_relationship_map",
            return_value=fake_result,
        ) as mock_run,
        patch(
            "endorlabs.workflows.estate.analyze.project_map.map.parse_args",
            return_value=SimpleNamespace(
                tenant="tenant.ns",
                namespace="tenant.ns",
                include_public=False,
                max_depth=2,
                max_pages=1,
                page_size=100,
                dep_metadata_max_pages=1,
                max_workers=4,
                output_dir=".tmp",
            ),
        ),
    ):
        code = rel_map.main()

    assert code == 0
    mock_run.assert_called_once()
    fake_client.close.assert_called_once()


def test_run_project_relationship_map_lists_dependency_metadata_per_project(
    tmp_path: Path,
) -> None:
    projects = [_project("p1", "repo-1", "tenant.ns")]
    pvs = [_package_version("p1", "npm://pkg-a@1.0.0")]

    fake_client = Mock()
    fake_client.Project.list.return_value = projects
    fake_client.PackageVersion.list.return_value = pvs
    fake_client.DependencyMetadata.list.return_value = []

    with patch(
        "endorlabs.workflows.estate.analyze.project_map.run.row_to_supporting_tuples",
        return_value=[],
    ):
        rel_run.run_project_relationship_map(
            fake_client,
            namespace="tenant.ns",
            output_dir=tmp_path,
            max_pages=1,
            page_size=100,
            dep_metadata_max_pages=1,
            max_workers=1,
        )

    fake_client.DependencyMetadata.list.assert_called_once()
    _args, kwargs = fake_client.DependencyMetadata.list.call_args
    assert kwargs.get("namespace") == "tenant.ns"
