"""Pure helpers for project relationship mapping (testable, no I/O)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from endorlabs.tools.dependency_explorer import parse_dep_name


@dataclass
class SupportingPackage:
    """One deduplicated package edge between consumer and producer project."""

    package_name: str
    package_version: str
    dependency_kind: str
    visibility: str
    evidence_tier: str
    ambiguous: bool = False
    _dedup: tuple[str, str, str, str] = field(repr=False, default=("", "", "", ""))


def add_producer_indices(
    package_meta_name: str,
    project_uuid: str,
    produced_by: dict[tuple[str, str], set[str]],
    produced_name_only: dict[str, set[str]],
) -> None:
    """Index one ``PackageVersion.meta.name`` and producer project UUID."""
    if not package_meta_name or not project_uuid:
        return
    pkg, ver = parse_dep_name(package_meta_name)
    produced_by.setdefault((pkg, ver or ""), set()).add(project_uuid)
    produced_name_only.setdefault(pkg, set()).add(project_uuid)


def _visibility_label(dd: dict[str, Any]) -> str:
    pub = dd.get("public")
    if pub is True:
        return "public"
    if pub is False:
        return "private"
    return "unknown"


def _extract_one_consumer_row(
    spec: dict[str, Any], include_public: bool
) -> dict[str, Any] | None:
    imp = (spec or {}).get("importer_data") or {}
    dd = (spec or {}).get("dependency_data") or {}
    consumer = imp.get("project_uuid")
    if not consumer:
        return None
    is_public = dd.get("public", None)
    if not include_public and is_public is True:
        return None
    return {
        "consumer": str(consumer),
        "package_name": str(dd.get("package_name") or ""),
        "version": str(
            dd.get("resolved_version") or dd.get("unresolved_version") or ""
        ),
        "direct": bool(dd.get("direct", False)),
        "visibility": _visibility_label(dd),
    }


def match_producer_projects(
    package_name: str,
    dep_version: str,
    produced_by: dict[tuple[str, str], set[str]],
    produced_name_only: dict[str, set[str]],
) -> list[tuple[str, str, bool]]:
    """(producer_project_uuid, tier, ambiguous) for a dependency name/version."""
    if not package_name:
        return []
    k = (package_name, dep_version or "")
    if produced_by.get(k):
        s = produced_by[k]
        amb = len(s) > 1
        return [(pu, "tier_a_exact", amb) for pu in s]
    s2 = produced_name_only.get(package_name, set())
    if s2:
        return [(pu, "tier_b_name_only", len(s2) > 1) for pu in s2]
    return []


def row_to_supporting_tuples(
    spec: dict[str, Any],
    project_uuids: set[str],
    include_public: bool,
    produced_by: dict[tuple[str, str], set[str]],
    produced_name_only: dict[str, set[str]],
) -> list[tuple[str, str, SupportingPackage]]:
    """Map one DependencyMetadata row to consumer→producer supporting tuples."""
    r = _extract_one_consumer_row(spec, include_public)
    if not r or r["consumer"] not in project_uuids:
        return []
    c, pnm, ver = r["consumer"], r["package_name"], r["version"]
    kind = "direct" if r["direct"] else "transitive"
    vis = r["visibility"]
    out: list[tuple[str, str, SupportingPackage]] = []
    for puuid, tier, amb in match_producer_projects(
        pnm, ver, produced_by, produced_name_only
    ):
        if c == puuid:
            continue
        if not puuid:
            continue
        out.append(
            (
                c,
                puuid,
                SupportingPackage(
                    package_name=pnm,
                    package_version=ver,
                    dependency_kind=kind,
                    visibility=vis,
                    evidence_tier=tier,
                    ambiguous=amb,
                ),
            )
        )
    return out


def _strongest_tier(has_exact: bool, has_b: bool) -> str:
    if has_exact and not has_b:
        return "tier_a_exact"
    if has_b and not has_exact:
        return "tier_b_name_only"
    if has_exact and has_b:
        return "tier_a_exact"
    return "tier_b_name_only"


def aggregate_project_edges(
    supporting: list[tuple[str, str, SupportingPackage]],
) -> list[dict[str, Any]]:
    """Build one record per (from, to) with ``supporting_packages`` and counts.

    Deduplicate supporting evidence by
    (consumer, producer, package_name, package_version) — strongest tier kept.
    """
    best: dict[tuple[str, str, str, str], SupportingPackage] = {}
    for fr, to, sp in supporting:
        if fr == to:
            continue
        k4 = (fr, to, sp.package_name, sp.package_version)
        if k4 not in best:
            best[k4] = sp
        else:
            o = best[k4]
            if sp.evidence_tier == "tier_a_exact" and o.evidence_tier != "tier_a_exact":
                best[k4] = sp
    pair_map: dict[tuple[str, str], list[SupportingPackage]] = {}
    for k4, sp in best.items():
        fr, to, _pn, _pv = k4
        pair_map.setdefault((fr, to), []).append(sp)
    out: list[dict[str, Any]] = []
    for (u, v), sps in pair_map.items():
        sp_list = sps
        has_e = any(x.evidence_tier == "tier_a_exact" for x in sp_list)
        has_b = any(x.evidence_tier == "tier_b_name_only" for x in sp_list)
        d_count = sum(1 for p in sp_list if p.dependency_kind == "direct")
        t_count = sum(1 for p in sp_list if p.dependency_kind == "transitive")
        p_pub = sum(1 for p in sp_list if p.visibility == "public")
        p_unk = sum(1 for p in sp_list if p.visibility == "unknown")
        p_prv = len(sp_list) - p_pub
        if p_unk:
            p_prv = p_prv - p_unk
        out.append(
            {
                "from_project_uuid": u,
                "to_project_uuid": v,
                "evidence_tier": _strongest_tier(has_e, has_b),
                "support_count": len(sp_list),
                "direct_support_count": d_count,
                "transitive_support_count": t_count,
                "private_support_count": p_prv,
                "public_support_count": p_pub,
                "supporting_packages": [
                    {
                        "package_name": p.package_name,
                        "package_version": p.package_version,
                        "dependency_kind": p.dependency_kind,
                        "visibility": p.visibility,
                        "evidence_tier": p.evidence_tier,
                        "ambiguous": p.ambiguous,
                    }
                    for p in sorted(
                        sp_list,
                        key=lambda x: (x.package_name, x.package_version),
                    )
                ],
            }
        )
    return out


def path_confidence_for_tiers(tiers: list[str]) -> str:
    """Map edge-tier sequence to high/medium/low path confidence."""
    if not tiers:
        return "low"
    if all(t == "tier_a_exact" for t in tiers):
        return "high"
    if all(t == "tier_b_name_only" for t in tiers):
        return "low"
    return "medium"


def bfs_min_path(
    start: str,
    goal: str,
    adj: dict[str, set[str]],
    edge_tier: dict[tuple[str, str], str],
    max_hops: int,
) -> tuple[list[str] | None, list[str] | None, int | None]:
    """Return shortest (path_nodes, path_edge_tiers, num_hops) with hop count <= max.

    *num_hops* is number of edges. Requires num_hops >= 2 to count as an indirect
    project-to-project path.
    """
    if start == goal:
        return None, None, None
    q: deque[tuple[str, list[str], list[str], int]] = deque([(start, [start], [], 0)])
    while q:
        node, pnodes, tiers, nh = q.popleft()
        for nbr in sorted(adj.get(node, set())):
            if nbr in pnodes:
                continue
            t = edge_tier.get((node, nbr), "tier_b_name_only")
            nn = nh + 1
            p2 = [*pnodes, nbr]
            t2 = [*tiers, t]
            if nbr == goal and nn >= 2 and nn <= max_hops:
                return p2, t2, nn
            if nn < max_hops:
                q.append((nbr, p2, t2, nn))
    return None, None, None


def build_adj_and_edge_tiers(
    edges: list[dict[str, Any]],
) -> tuple[dict[str, set[str]], dict[tuple[str, str], str]]:
    """Directed graph: consumer -> producer. Strongest edge tier wins per (u, v)."""
    best: dict[tuple[str, str], str] = {}
    for e in edges:
        u = e.get("from_project_uuid")
        w = e.get("to_project_uuid")
        if not u or not w or u == w:
            continue
        u_s, w_s = str(u), str(w)
        tv: str = str(e.get("evidence_tier") or "tier_b_name_only")
        k = (u_s, w_s)
        if k not in best:
            best[k] = tv
        elif best[k] != "tier_a_exact" and tv == "tier_a_exact":
            best[k] = "tier_a_exact"
    adj: dict[str, set[str]] = {}
    for u, w in best:
        adj.setdefault(u, set()).add(w)
    return adj, best


def indirect_paths_bfs(
    project_uuids: list[str],
    direct_edges: list[dict[str, Any]],
    max_hops: int,
) -> list[dict[str, Any]]:
    """List one shortest path per (src, tgt) where hop count in [2, *max_hops*]."""
    if max_hops < 2:
        return []
    adj, edge_t = build_adj_and_edge_tiers(direct_edges)
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for src in project_uuids:
        for tgt in project_uuids:
            if src == tgt or (src, tgt) in seen:
                continue
            path, e_t, nh = bfs_min_path(str(src), str(tgt), adj, edge_t, max_hops)
            if not path or nh is None or nh < 2:
                continue
            seen.add((str(src), str(tgt)))
            out.append(
                {
                    "source_project_uuid": src,
                    "target_project_uuid": tgt,
                    "hop_count": nh,
                    "path_project_uuids": path,
                    "path_edge_tiers": e_t,
                    "confidence": path_confidence_for_tiers(e_t or []),
                }
            )
    return out
