"""Tests for QueryScope builders and batching."""

from __future__ import annotations

from types import SimpleNamespace

from endorlabs.query.scope import QueryScope, scopes_from_projects
from endorlabs.query.spec import QuerySpec
from endorlabs.query.topology import DiscoveredProject, TopologySnapshot


def test_scopes_from_projects_groups_by_namespace() -> None:
    projects = [
        SimpleNamespace(
            uuid="p1",
            tenant_meta=SimpleNamespace(namespace="tenant.child-a"),
        ),
        SimpleNamespace(
            uuid="p2",
            tenant_meta=SimpleNamespace(namespace="tenant.child-a"),
        ),
        SimpleNamespace(
            uuid="p3",
            tenant_meta=SimpleNamespace(namespace="tenant.child-b"),
        ),
    ]
    scopes = scopes_from_projects(projects)
    assert scopes == [
        QueryScope(namespace="tenant.child-a", keys=("p1", "p2")),
        QueryScope(namespace="tenant.child-b", keys=("p3",)),
    ]


def test_query_spec_for_scope_batch_adds_uuid_filter() -> None:
    spec = QuerySpec.root("Project").leaf_scope()
    wire = spec.for_scope_batch(("a", "b"))
    filt = wire["list_parameters"]["filter"]
    assert 'uuid in ["a", "b"]' in filt or 'uuid in ["a","b"]' in filt.replace(" ", "")


def test_topology_query_scopes_match_geometry() -> None:
    topo = TopologySnapshot(
        tenant="tenant",
        project_count=2,
        namespace_count=1,
        max_projects_per_namespace=2,
        archetype="mixed",
        projects=[
            DiscoveredProject(uuid="p1", name="a", namespace="tenant.child"),
            DiscoveredProject(uuid="p2", name="b", namespace="tenant.child"),
        ],
    )
    scopes = topo.query_scopes()
    assert len(scopes) == 1
    assert scopes[0].namespace == "tenant.child"
    assert scopes[0].keys == ("p1", "p2")
    shards = topo.project_shards()
    assert len(shards) == 2
    assert {s.project_uuid for s in shards} == {"p1", "p2"}
