"""Tests for relationships.map CLI flow."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

from endorlabs.workflows.relationships import map as rel_map


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
    assert rel_map._object_to_spec_dict(dumped) == {"a": 1}
    assert rel_map._object_to_spec_dict({"spec": {"b": 2}}) == {"b": 2}
    assert rel_map._object_to_spec_dict("bad") == {}


def test_main_writes_graph_artifacts_and_closes_client() -> None:
    projects = [_project("p1", "repo-1", "tenant.ns")]
    pvs = [_package_version("p1", "pkg-a@1.0.0")]
    dep_rows = [{"supporting_packages": [{"name": "pkg-a", "version": "1.0.0"}]}]

    fake_client = Mock()
    fake_client.Project.list.return_value = projects
    fake_client.PackageVersion.list.return_value = pvs
    fake_client.DependencyMetadata.list.return_value = dep_rows

    with (
        patch(
            "endorlabs.workflows.relationships.map.endorlabs.Client",
            return_value=fake_client,
        ),
        patch(
            "endorlabs.workflows.relationships.map.row_to_supporting_tuples",
            return_value=[("p1", "p1", {"name": "pkg-a"})],
        ),
        patch(
            "endorlabs.workflows.relationships.map.aggregate_project_edges",
            return_value=[
                {
                    "source_project_uuid": "p1",
                    "target_project_uuid": "p1",
                    "evidence_tier": "tier_a_exact",
                }
            ],
        ),
        patch(
            "endorlabs.workflows.relationships.map.indirect_paths_bfs", return_value=[]
        ),
        patch("endorlabs.workflows.relationships.map.write_json") as mock_write_json,
        patch(
            "endorlabs.workflows.relationships.map.parse_args",
            return_value=SimpleNamespace(
                tenant="tenant.ns",
                namespace="tenant.ns",
                include_public=False,
                max_depth=2,
                max_pages=1,
                page_size=100,
                dep_metadata_max_pages=1,
                output_dir=".tmp",
            ),
        ),
    ):
        code = rel_map.main()

    assert code == 0
    assert mock_write_json.call_count == 3
    fake_client.close.assert_called_once()
