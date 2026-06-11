"""Tests for scan result list helpers in troubleshooting workflows."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

from endorlabs.client_surface import Client
from endorlabs.workflows.troubleshooting_scans.common import (
    list_scan_results_for_project,
    object_to_dict,
    parallel_collect_for_projects,
)


def test_list_scan_results_for_project_uses_parent_filter() -> None:
    client = MagicMock(spec=Client)
    client.ScanResult = Mock()
    sr1 = Mock()
    sr1.model_dump = Mock(
        return_value={
            "uuid": "sr1",
            "meta": {"parent_uuid": "p1"},
            "spec": {"status": "STATUS_SUCCESS"},
        }
    )
    sr2 = Mock()
    sr2.model_dump = Mock(
        return_value={
            "uuid": "sr2",
            "meta": {"parent_uuid": "p1"},
            "spec": {"status": "STATUS_FAILED"},
        }
    )
    client.ScanResult.list = Mock(return_value=[sr1, sr2])

    results = list_scan_results_for_project(
        client,
        namespace="tenant.child",
        project_uuid="p1",
        limit=10,
        status_filter="STATUS_SUCCESS",
    )

    client.ScanResult.list.assert_called_once()
    kwargs = client.ScanResult.list.call_args.kwargs
    assert kwargs["namespace"] == "tenant.child"
    assert kwargs["filter"] == 'meta.parent_uuid=="p1"'
    assert kwargs["sort_by"] == "meta.create_time"
    assert kwargs["desc"] is True
    assert kwargs["max_pages"] == 1
    assert kwargs["page_size"] == 10
    assert len(results) == 1
    assert results[0]["uuid"] == "sr1"


def test_object_to_dict_passthrough() -> None:
    assert object_to_dict({"a": 1}) == {"a": 1}


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
