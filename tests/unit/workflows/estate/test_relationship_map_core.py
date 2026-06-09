"""Unit tests for project relationship map pure helpers."""

from __future__ import annotations

from endorlabs.tools.dependency_explorer import parse_dep_name
from endorlabs.workflows.estate.analyze.project_map.core import (
    SupportingPackage,
    _extract_one_consumer_row,
    _visibility_label,
    add_producer_indices,
    aggregate_project_edges,
    bfs_min_path,
    build_adj_and_edge_tiers,
    indirect_paths_bfs,
    match_producer_projects,
    path_confidence_for_tiers,
    row_to_supporting_tuples,
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


def test_visibility_label_variants() -> None:
    assert _visibility_label({"public": True}) == "public"
    assert _visibility_label({"public": False}) == "private"
    assert _visibility_label({}) == "unknown"


def test_extract_consumer_row_filters_public_when_disabled() -> None:
    spec = {
        "importer_data": {"project_uuid": "c1"},
        "dependency_data": {"public": True, "package_name": "npm://x"},
    }
    assert _extract_one_consumer_row(spec, include_public=False) is None
    row = _extract_one_consumer_row(spec, include_public=True)
    assert row is not None
    assert row["consumer"] == "c1"
    assert row["package_name"] == "npm://x"


def test_match_producer_projects_prefers_exact_then_name_only() -> None:
    produced_by = {("npm://x", "1.0.0"): {"p1", "p2"}}
    produced_name_only = {"npm://x": {"p3"}}
    exact = match_producer_projects("npm://x", "1.0.0", produced_by, produced_name_only)
    assert {x[0] for x in exact} == {"p1", "p2"}
    assert all(x[1] == "tier_a_exact" for x in exact)
    name_only = match_producer_projects(
        "npm://x", "9.9.9", produced_by, produced_name_only
    )
    assert name_only == [("p3", "tier_b_name_only", False)]


def test_row_to_supporting_tuples_skips_self_and_unknown() -> None:
    spec = {
        "importer_data": {"project_uuid": "c1"},
        "dependency_data": {
            "package_name": "npm://x",
            "resolved_version": "1.0.0",
            "public": False,
            "direct": True,
        },
    }
    produced_by = {("npm://x", "1.0.0"): {"", "c1", "p1"}}
    out = row_to_supporting_tuples(
        spec,
        {"c1"},
        include_public=True,
        produced_by=produced_by,
        produced_name_only={},
    )
    assert len(out) == 1
    assert out[0][0] == "c1"
    assert out[0][1] == "p1"
    assert out[0][2].dependency_kind == "direct"


def test_build_adj_and_edge_tiers_ignores_self_and_keeps_strongest() -> None:
    adj, tiers = build_adj_and_edge_tiers(
        [
            {
                "from_project_uuid": "A",
                "to_project_uuid": "A",
                "evidence_tier": "tier_b_name_only",
            },
            {
                "from_project_uuid": "A",
                "to_project_uuid": "B",
                "evidence_tier": "tier_b_name_only",
            },
            {
                "from_project_uuid": "A",
                "to_project_uuid": "B",
                "evidence_tier": "tier_a_exact",
            },
        ]
    )
    assert "A" in adj and "B" in adj["A"]
    assert tiers[("A", "B")] == "tier_a_exact"


def test_bfs_min_path_returns_none_when_start_equals_goal() -> None:
    path, tiers, hops = bfs_min_path("A", "A", {}, {}, 3)
    assert path is None and tiers is None and hops is None


def test_indirect_paths_bfs_requires_min_hops_two() -> None:
    edges = [
        {
            "from_project_uuid": "A",
            "to_project_uuid": "B",
            "evidence_tier": "tier_a_exact",
        }
    ]
    assert indirect_paths_bfs(["A", "B"], edges, 1) == []


def test_aggregate_project_edges_private_count_ignores_unknown() -> None:
    items = [
        (
            "c1",
            "p1",
            SupportingPackage(
                package_name="npm://x",
                package_version="1",
                dependency_kind="transitive",
                visibility="unknown",
                evidence_tier="tier_b_name_only",
            ),
        ),
        (
            "c1",
            "p1",
            SupportingPackage(
                package_name="npm://y",
                package_version="1",
                dependency_kind="direct",
                visibility="public",
                evidence_tier="tier_b_name_only",
            ),
        ),
    ]
    out = aggregate_project_edges(items)
    assert out[0]["private_support_count"] == 0
    assert out[0]["public_support_count"] == 1
    assert out[0]["direct_support_count"] == 1
    assert out[0]["transitive_support_count"] == 1


def test_path_confidence_empty_is_low() -> None:
    assert path_confidence_for_tiers([]) == "low"


def test_bfs_min_path_avoids_cycles_and_respects_max_hops() -> None:
    adj = {"A": {"B"}, "B": {"A", "C"}}
    tiers = {
        ("A", "B"): "tier_a_exact",
        ("B", "A"): "tier_b_name_only",
        ("B", "C"): "tier_a_exact",
    }
    path, _edge_tiers, hops = bfs_min_path("A", "C", adj, tiers, 2)
    assert path == ["A", "B", "C"]
    assert hops == 2
