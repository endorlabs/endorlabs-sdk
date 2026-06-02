"""Unit tests for analytics version-cardinality export."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from endorlabs.workflows.analytics.export_dependencies import (
    export_version_cardinality,
    export_version_cardinality_for_package_match,
    main,
)
from endorlabs.workflows.analytics.group_list import parse_group_key


def _mock_project(uuid: str, namespace: str) -> MagicMock:
    project = MagicMock()
    project.uuid = uuid
    project.tenant_meta.namespace = namespace
    return project


def _mock_package_version(uuid: str) -> MagicMock:
    package_version = MagicMock()
    package_version.uuid = uuid
    return package_version


def test_parse_group_key_composite() -> None:
    key = json.dumps(
        [
            {"key": "spec.dependency_data.package_name", "value": "go://pkg"},
            {"key": "spec.dependency_data.resolved_version", "value": "v1.2.3"},
        ]
    )
    parsed = parse_group_key(key)
    assert parsed["spec.dependency_data.package_name"] == "go://pkg"
    assert parsed["spec.dependency_data.resolved_version"] == "v1.2.3"


def test_export_version_cardinality_rollup() -> None:
    group_key = json.dumps(
        [
            {"key": "spec.dependency_data.package_name", "value": "pypi://django"},
            {"key": "spec.dependency_data.resolved_version", "value": "4.2"},
        ]
    )
    group_key2 = json.dumps(
        [
            {"key": "spec.dependency_data.package_name", "value": "pypi://django"},
            {"key": "spec.dependency_data.resolved_version", "value": "5.0"},
        ]
    )

    client = MagicMock()
    client.Project.list.return_value = [_mock_project("proj-1", "tenant")]
    client.PackageVersion.list.return_value = [_mock_package_version("pv-1")]

    def _buckets(
        _client: MagicMock,
        namespace: str,
        list_params: object,
        *,
        max_pages: int | None = None,
    ) -> list[tuple[str, dict[str, object]]]:
        _ = max_pages
        assert namespace == "tenant"
        assert getattr(list_params, "filter", None) == (
            'spec.importer_data.package_version_uuid=="pv-1"'
        )
        return [
            (group_key, {"aggregation_count": {"count": 10}}),
            (group_key2, {"aggregation_count": {"count": 3}}),
        ]

    with (
        patch(
            "endorlabs.workflows.analytics.export_dependencies.iter_group_buckets",
            side_effect=_buckets,
        ),
        patch(
            "endorlabs.workflows.analytics.export_dependencies.discover_estate_namespace_names",
            return_value=["tenant"],
        ),
        patch(
            "endorlabs.workflows.analytics.export_dependencies.namespaces_for_grouped_counts",
            return_value=["tenant"],
        ),
    ):
        result = export_version_cardinality(client, "tenant", progress_batch=1)

    assert result.status == "success"
    assert result.table.row_count == 1
    row = result.table.rows[0]
    assert row["package_name"] == "pypi://django"
    assert row["version_cardinality"] == 2
    assert row["dependency_usage_rows"] == 13
    assert result.stats.name_version_group_count == 2
    assert result.stats.namespace_count == 1
    assert result.stats.project_count == 1
    assert result.stats.importer_package_version_count == 1


def test_export_merges_counts_across_namespaces() -> None:
    group_key = json.dumps(
        [
            {"key": "spec.dependency_data.package_name", "value": "pypi://django"},
            {"key": "spec.dependency_data.resolved_version", "value": "4.2"},
        ]
    )
    client = MagicMock()

    def _projects(namespace: str | None = None, **kwargs: object) -> list[MagicMock]:
        _ = kwargs
        if namespace == "tenant.a":
            return [_mock_project("proj-a", "tenant.a")]
        if namespace == "tenant.b":
            return [_mock_project("proj-b", "tenant.b")]
        return []

    client.Project.list.side_effect = _projects

    def _package_versions(
        namespace: str | None = None, **kwargs: object
    ) -> list[MagicMock]:
        _ = kwargs
        if namespace == "tenant.a":
            return [_mock_package_version("pv-a")]
        if namespace == "tenant.b":
            return [_mock_package_version("pv-b")]
        return []

    client.PackageVersion.list.side_effect = _package_versions

    def _buckets(
        _client: MagicMock,
        namespace: str,
        _list_params: object,
        *,
        max_pages: int | None = None,
    ) -> list[tuple[str, dict[str, object]]]:
        _ = max_pages
        count = 10 if namespace == "tenant.a" else 7
        return [(group_key, {"aggregation_count": {"count": count}})]

    with (
        patch(
            "endorlabs.workflows.analytics.export_dependencies.iter_group_buckets",
            side_effect=_buckets,
        ),
        patch(
            "endorlabs.workflows.analytics.export_dependencies.discover_estate_namespace_names",
            return_value=["tenant", "tenant.a", "tenant.b"],
        ),
        patch(
            "endorlabs.workflows.analytics.export_dependencies.namespaces_for_grouped_counts",
            return_value=["tenant.a", "tenant.b"],
        ),
    ):
        result = export_version_cardinality(
            client,
            "tenant",
            progress_batch=0,
            include_usage_detail=True,
        )

    assert result.status == "success"
    assert result.table.rows[0]["dependency_usage_rows"] == 17
    assert result.stats.namespace_count == 2
    assert result.stats.project_count == 2
    assert result.stats.importer_package_version_count == 2
    assert result.usage_by_name_version.rows[0]["project_uuid"] == "proj-a"


def test_export_package_name_match_skips_project_shard() -> None:
    group_key = json.dumps(
        [
            {"key": "spec.dependency_data.package_name", "value": "pypi://django"},
            {"key": "spec.dependency_data.resolved_version", "value": "4.2"},
        ]
    )
    client = MagicMock()

    def _buckets(
        _client: MagicMock,
        namespace: str,
        list_params: object,
        *,
        max_pages: int | None = None,
    ) -> list[tuple[str, dict[str, object]]]:
        _ = max_pages
        assert namespace == "tenant"
        assert getattr(list_params, "filter", None) == (
            'spec.dependency_data.package_name.matches("django")'
        )
        return [(group_key, {"aggregation_count": {"count": 4}})]

    with (
        patch(
            "endorlabs.workflows.analytics.export_dependencies.iter_group_buckets",
            side_effect=_buckets,
        ),
        patch(
            "endorlabs.workflows.analytics.export_dependencies.discover_estate_namespace_names",
            return_value=["tenant"],
        ),
        patch(
            "endorlabs.workflows.analytics.export_dependencies.namespaces_for_grouped_counts",
            return_value=["tenant"],
        ),
    ):
        result = export_version_cardinality_for_package_match(
            client,
            "tenant",
            "django",
            exact_package_name="pypi://django",
        )

    client.Project.list.assert_not_called()
    assert result.status == "success"
    assert result.table.rows[0]["version_cardinality"] == 1
    assert result.stats.project_count == 0


@patch("endorlabs.workflows.analytics.export_dependencies.write_table")
@patch("endorlabs.workflows.analytics.export_dependencies.endorlabs.Client")
def test_main_writes_cardinality_csv(
    mock_client_cls: MagicMock,
    mock_write_table: MagicMock,
    tmp_path: object,
) -> None:
    out = tmp_path / "cardinality.csv"
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.side_effect = lambda *_args: mock_client.close()
    mock_client_cls.return_value = mock_client
    mock_client.Project.list.return_value = [_mock_project("proj-1", "tenant")]
    mock_client.PackageVersion.list.return_value = [_mock_package_version("pv-1")]

    group_key = json.dumps(
        [
            {"key": "spec.dependency_data.package_name", "value": "pypi://requests"},
            {"key": "spec.dependency_data.resolved_version", "value": "2.31"},
        ]
    )

    with (
        patch(
            "endorlabs.workflows.analytics.export_dependencies.iter_group_buckets",
            return_value=[(group_key, {"aggregation_count": {"count": 1}})],
        ),
        patch(
            "endorlabs.workflows.analytics.export_dependencies.discover_estate_namespace_names",
            return_value=["tenant"],
        ),
        patch(
            "endorlabs.workflows.analytics.export_dependencies.namespaces_for_grouped_counts",
            return_value=["tenant"],
        ),
    ):
        code = main(["--namespace", "tenant", "--output", str(out)])

    assert code == 0
    mock_write_table.assert_called_once()
    mock_client.close.assert_called_once()
