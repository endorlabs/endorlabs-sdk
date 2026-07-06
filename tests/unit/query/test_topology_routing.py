"""Tests for topology, routing, validate, and QueryFacade."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from endorlabs.facade import QueryFacade
from endorlabs.query import (
    OutputShape,
    TopologySnapshot,
    discover_topology,
    infer_archetype,
    recommend,
    validate_sample,
)


def test_infer_archetype_estate_sprawl() -> None:
    assert infer_archetype(9000, 148, 200) == "estate_sprawl"


def test_infer_archetype_monorepo_hub() -> None:
    assert infer_archetype(5000, 2, 5000) == "monorepo_hub"


def test_recommend_finding_log_trends() -> None:
    plan = recommend(OutputShape.FINDING_LOG_TRENDS)
    assert plan.primary == "facade_list_groups"
    assert plan.validate_recommended is False


def test_recommend_count_with_topology() -> None:
    topo = TopologySnapshot(
        tenant="tenant.root",
        project_count=100,
        namespace_count=50,
        max_projects_per_namespace=20,
        archetype="estate_sprawl",
    )
    plan = recommend(OutputShape.COUNT_BY_PROJECT, topology=topo)
    assert plan.primary == "query"
    assert plan.shard_key == "leaf_namespace"
    assert plan.validate_recommended is True


def test_discover_topology_dedupes_and_shards() -> None:
    client = MagicMock()
    client.Project.list.return_value = [
        {
            "uuid": "p1",
            "meta": {"name": "repo-a"},
            "tenant_meta": {"namespace": "tenant.child"},
        },
        {
            "uuid": "p1",
            "meta": {"name": "repo-a"},
            "tenant_meta": {"namespace": "tenant.child.deep"},
        },
        {
            "uuid": "p2",
            "meta": {"name": "repo-b"},
            "tenant_meta": {"namespace": "tenant.other"},
        },
    ]
    topo = discover_topology(client, "tenant.root", traverse=True)
    assert topo.project_count == 2
    assert topo.namespace_count == 2
    assert topo.projects[0].namespace == "tenant.child.deep"


def test_validate_sample_pv_match() -> None:
    projects = [SimpleNamespace(uuid="p1", namespace="tenant.leaf")]

    class _Query:
        def create(self, *, payload: Any, namespace: str) -> dict[str, Any]:
            _ = payload
            return {
                "spec": {
                    "query_response": {
                        "list": {
                            "objects": [
                                {
                                    "uuid": "p1",
                                    "meta": {
                                        "references": {
                                            "PackageVersion": {
                                                "count_response": {"count": 3}
                                            }
                                        }
                                    },
                                }
                            ]
                        }
                    }
                }
            }

    client = SimpleNamespace(
        Query=_Query(),
        PackageVersion=SimpleNamespace(
            count=lambda *, namespace, filter: 3  # noqa: ARG005
        ),
    )
    result = validate_sample(client, projects, recipe="pv", sample_size=1)
    assert result.matched is True


def test_query_facade_delegates_create_to_inner() -> None:
    inner = MagicMock()
    inner.create.return_value = {"uuid": "q1"}
    facade = QueryFacade.__new__(QueryFacade)
    facade._inner = inner
    facade._default_namespace = "tenant.root"
    assert facade.create(payload={"meta": {"name": "x"}}) == {"uuid": "q1"}
    inner.create.assert_called_once()
