"""Tests for scan result list helpers in troubleshooting workflows."""

from __future__ import annotations

from unittest.mock import Mock

from endorlabs.workflows.troubleshooting_scans.common import (
    list_scan_results_for_project,
    parallel_collect_for_projects,
)


def test_list_scan_results_for_project_uses_parent_filter() -> None:
    api = Mock()
    api.get_all.return_value = [
        {
            "uuid": "sr1",
            "meta": {"parent_uuid": "p1"},
            "spec": {"status": "STATUS_SUCCESS"},
        },
        {
            "uuid": "sr2",
            "meta": {"parent_uuid": "p1"},
            "spec": {"status": "STATUS_FAILED"},
        },
    ]

    results = list_scan_results_for_project(
        api,
        namespace="tenant.child",
        project_uuid="p1",
        limit=10,
        status_filter="STATUS_SUCCESS",
    )

    api.get_all.assert_called_once()
    path, kwargs = api.get_all.call_args[0][0], api.get_all.call_args[1]
    assert path == "v1/namespaces/tenant.child/scan-results"
    params = kwargs["params"]
    assert params["list_parameters.filter"] == 'meta.parent_uuid=="p1"'
    assert params["list_parameters.sort_path"] == "meta.create_time"
    assert params["list_parameters.sort_order"] == "descending"
    assert len(results) == 1
    assert results[0]["uuid"] == "sr1"


def test_parallel_collect_for_projects_flattens() -> None:
    projects = [
        {"uuid": "p1", "tenant_meta": {"namespace": "ns1"}},
        {"uuid": "p2", "tenant_meta": {"namespace": "ns2"}},
    ]

    def _fetch(shard: object) -> list[str]:
        from endorlabs.workflows.estate.collect.shards import ParentShard

        assert isinstance(shard, ParentShard)
        return [f"{shard.key}-a", f"{shard.key}-b"]

    out = parallel_collect_for_projects(
        projects,
        _fetch,
        max_workers=2,
        fallback_ns="fallback",
        progress_label="test projects",
    )
    assert sorted(out) == ["p1-a", "p1-b", "p2-a", "p2-b"]
