"""Unit tests for project relationship map pure helpers."""

from __future__ import annotations

from endorlabs.tools.dependency_explorer import parse_dep_name
from endorlabs.workflows.relationships.core import (
    SupportingPackage,
    add_producer_indices,
    aggregate_project_edges,
    bfs_min_path,
    build_adj_and_edge_tiers,
    indirect_paths_bfs,
    path_confidence_for_tiers,
)


def test_add_producer_indices() -> None:
    pb: dict = {}
    pn: dict = {}
    add_producer_indices("npm://a@1.0.0", "P1", pb, pn)
    a, b = parse_dep_name("npm://a@1.0.0")
    assert a == "npm://a"
    assert b == "1.0.0"
    k = ("npm://a", "1.0.0")
    assert k in pb
    assert "P1" in pb[k]


def test_path_confidence() -> None:
    assert path_confidence_for_tiers(["tier_a_exact", "tier_a_exact"]) == "high"
    assert path_confidence_for_tiers(["tier_b_name_only"]) == "low"
    assert path_confidence_for_tiers(["tier_a_exact", "tier_b_name_only"]) == "medium"


def test_bfs_min_path() -> None:
    adj, et = build_adj_and_edge_tiers(
        [
            {
                "from_project_uuid": "A",
                "to_project_uuid": "B",
                "evidence_tier": "tier_a_exact",
            },
            {
                "from_project_uuid": "B",
                "to_project_uuid": "C",
                "evidence_tier": "tier_b_name_only",
            },
        ]
    )
    path, _ti, nh = bfs_min_path("A", "C", adj, et, 3)
    assert path == ["A", "B", "C"]
    assert nh == 2


def test_indirect_only_two_hop() -> None:
    e = [
        {
            "from_project_uuid": "A",
            "to_project_uuid": "B",
            "evidence_tier": "tier_a_exact",
        }
    ]
    p = indirect_paths_bfs(["A", "B"], e, 3)
    # A->B is one hop: no indirect (>=2 hops) path
    assert p == []


def test_aggregate_dedup_tier() -> None:
    sp1 = [
        (
            "c1",
            "p1",
            SupportingPackage(
                package_name="npm://x",
                package_version="1",
                dependency_kind="direct",
                visibility="private",
                evidence_tier="tier_b_name_only",
            ),
        ),
        (
            "c1",
            "p1",
            SupportingPackage(
                package_name="npm://x",
                package_version="1",
                dependency_kind="direct",
                visibility="private",
                evidence_tier="tier_a_exact",
            ),
        ),
    ]
    out = aggregate_project_edges(sp1)
    assert len(out) == 1
    assert out[0]["evidence_tier"] == "tier_a_exact"
    assert out[0]["support_count"] == 1
