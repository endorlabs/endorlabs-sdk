"""Tests for topology_to_project_shards adapter."""

from __future__ import annotations

from types import SimpleNamespace

from endorlabs.query import TopologySnapshot
from endorlabs.tools.list_sharding import topology_to_project_shards


def test_topology_to_project_shards_from_snapshot() -> None:
    topo = TopologySnapshot(
        tenant="tenant.root",
        project_count=2,
        namespace_count=1,
        max_projects_per_namespace=2,
        archetype="single_repo",
        projects=[
            SimpleNamespace(uuid="p1", name="repo-a", namespace="tenant.child"),
            SimpleNamespace(uuid="p2", name="repo-b", namespace="tenant.child"),
        ],
    )
    shards = topology_to_project_shards(topo, fallback_ns="tenant.root")
    assert len(shards) == 2
    assert shards[0].project_uuid == "p1"
    assert shards[0].namespace == "tenant.child"
    assert shards[0].label == "repo-a"
