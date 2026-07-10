"""Tests for shared troubleshooting scan helpers."""

from __future__ import annotations

from endorlabs.utils.serialization import object_to_dict
from endorlabs.workflows.troubleshooting_scans.common import (
    parallel_collect_for_projects,
)


def test_object_to_dict_passthrough() -> None:
    assert object_to_dict({"a": 1}) == {"a": 1}


def test_parallel_collect_for_projects_flattens() -> None:
    projects = [
        {"uuid": "p1", "tenant_meta": {"namespace": "ns1"}},
        {"uuid": "p2", "tenant_meta": {"namespace": "ns2"}},
    ]

    def _fetch(shard: object) -> list[str]:
        from endorlabs.tools.list_sharding import ProjectShard

        assert isinstance(shard, ProjectShard)
        return [f"{shard.project_uuid}-a", f"{shard.project_uuid}-b"]

    out = parallel_collect_for_projects(
        projects,
        _fetch,
        max_workers=2,
        fallback_ns="fallback",
        progress_label="test projects",
    )
    assert sorted(out) == ["p1-a", "p1-b", "p2-a", "p2-b"]
