"""Derive Call Graph URI patterns from AI-SAST seeds and match/walk."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any, cast

from endorlabs.workflows.callgraph.graph import (
    build_uri_index,
    resolve_method_ids_by_patterns,
)
from endorlabs.workflows.callgraph.path import find_call_graph_path

_FQN_SPLIT = re.compile(r"[./:#]+")


def _basename_stem(file_path: str | None) -> str | None:
    if not file_path:
        return None
    name = PurePosixPath(file_path.replace("\\", "/")).name
    if not name:
        return None
    stem = name.rsplit(".", 1)[0]
    return stem or None


def _fqn_tail(fqn: str | None) -> str | None:
    if not fqn:
        return None
    parts = [p for p in _FQN_SPLIT.split(str(fqn)) if p]
    if not parts:
        return None
    # Drop trivial empty / constructor noise
    tail = parts[-1]
    if tail in {"()", "constructor"} and len(parts) >= 2:
        return parts[-2]
    return tail


def patterns_from_seed(seed: dict[str, Any]) -> list[str]:
    """Build CG URI substring patterns from one seed (never uses rest_path)."""
    stem = _basename_stem(
        str(seed["file_path"]) if seed.get("file_path") is not None else None
    )
    fqn_tail = _fqn_tail(str(seed["fqn"]) if seed.get("fqn") is not None else None)
    file_path = seed.get("file_path")
    parent: str | None = None
    if file_path:
        parts = PurePosixPath(str(file_path).replace("\\", "/")).parts
        if len(parts) >= 2:
            cand = parts[-2]
            if cand not in {".", ".."} and cand.lower() not in {
                "src",
                "app",
                "lib",
                "pkg",
            }:
                parent = cand

    # routes/login-style paths are strong CG URI anchors
    if parent and stem:
        path_pat = f"{parent}/{stem}"
        if fqn_tail and fqn_tail.lower() not in {stem.lower(), parent.lower()}:
            return [path_pat, fqn_tail]
        return [path_pat]

    if stem and fqn_tail and fqn_tail.lower() != stem.lower():
        return [stem, fqn_tail]
    if stem:
        return [stem]
    if fqn_tail:
        return [fqn_tail]
    return []


def match_seeds_to_callables(
    seeds: list[dict[str, Any]],
    callables: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Match each seed's patterns to CG callable URIs."""
    uri_by_id = build_uri_index(callables)
    rows: list[dict[str, Any]] = []
    for seed in seeds:
        patterns = patterns_from_seed(seed)
        method_ids = (
            resolve_method_ids_by_patterns(callables, patterns) if patterns else []
        )
        matched_uris = [uri_by_id[mid] for mid in method_ids if mid in uri_by_id]
        rows.append(
            {
                "seed": {
                    "fqn": seed.get("fqn"),
                    "file_path": seed.get("file_path"),
                    "line_start": seed.get("line_start"),
                    "rest_path": seed.get("rest_path"),
                    "is_entry_point": seed.get("is_entry_point"),
                },
                "path_from_patterns": patterns,
                "matched_method_ids": method_ids,
                "matched_uris": matched_uris[:20],
                "match_count": len(method_ids),
            }
        )
    return rows


# Hard caps for agent-safe BFS (callers may pass lower values).
_MAX_DEPTH_CAP = 12
_MAX_PATHS_CAP = 20
_DEFAULT_MAX_SOURCE_IDS = 40

WALK_DISCLAIMER = (
    "Call-graph path existence is not Finding REACHABLE_FUNCTION evidence; "
    "use endor-reachability-provenance for Finding/oss stitch."
)


def clamp_walk_bounds(
    *,
    max_depth: int = 6,
    max_paths: int = 5,
    max_source_ids: int = _DEFAULT_MAX_SOURCE_IDS,
) -> tuple[int, int, int]:
    """Clamp BFS bounds to safe ranges."""
    depth = max(1, min(int(max_depth), _MAX_DEPTH_CAP))
    paths = max(1, min(int(max_paths), _MAX_PATHS_CAP))
    sources = max(1, min(int(max_source_ids), 200))
    return depth, paths, sources


def walk_from_matches(
    callables: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    matches: list[dict[str, Any]],
    *,
    path_to: list[str],
    max_depth: int = 6,
    max_paths: int = 5,
    max_source_ids: int = _DEFAULT_MAX_SOURCE_IDS,
) -> list[dict[str, Any]]:
    """BFS from each matched seed's patterns to *path_to* patterns.

    Safety:
    - Clamps ``max_depth`` / ``max_paths``
    - Skips seeds whose pattern fanout exceeds ``max_source_ids``
    - Skips when target patterns resolve to zero callables
    - Annotates that CG path ≠ Finding reachability
    """
    if not path_to:
        return []
    # Advisory ids must never be CG URI patterns
    from endorlabs.workflows.aisast_callgraph.targets import is_vuln_id_shaped

    cleaned = [p for p in path_to if p and not is_vuln_id_shaped(str(p))]
    if not cleaned:
        return [
            {
                "path_to_patterns": list(path_to),
                "path_found": False,
                "paths": [],
                "skipped": "path_to_was_vuln_id_only",
                "cg_path_is_not_finding_reachability": True,
                "disclaimer": WALK_DISCLAIMER,
            }
        ]

    depth, paths_cap, source_cap = clamp_walk_bounds(
        max_depth=max_depth,
        max_paths=max_paths,
        max_source_ids=max_source_ids,
    )
    target_ids = resolve_method_ids_by_patterns(callables, cleaned)

    walks: list[dict[str, Any]] = []
    for row in matches:
        raw_patterns = row.get("path_from_patterns")
        patterns: list[str] = (
            [str(p) for p in cast("list[Any]", raw_patterns)]
            if isinstance(raw_patterns, list)
            else []
        )
        base: dict[str, Any] = {
            "seed": row.get("seed"),
            "path_from_patterns": patterns,
            "path_to_patterns": cleaned,
            "path_found": False,
            "paths": [],
            "max_depth": depth,
            "cg_path_is_not_finding_reachability": True,
            "disclaimer": WALK_DISCLAIMER,
        }
        if not patterns or not row.get("match_count"):
            walks.append({**base, "skipped": "no_cg_match"})
            continue
        if not target_ids:
            walks.append({**base, "skipped": "target_not_in_callgraph"})
            continue
        source_ids = resolve_method_ids_by_patterns(callables, list(patterns))
        if len(source_ids) > source_cap:
            walks.append(
                {
                    **base,
                    "skipped": "source_fanout_too_high",
                    "source_id_count": len(source_ids),
                    "max_source_ids": source_cap,
                }
            )
            continue
        result = find_call_graph_path(
            callables,
            edges,
            from_patterns=list(patterns),
            to_patterns=list(cleaned),
            max_depth=depth,
            max_paths=paths_cap,
        )
        walks.append(
            {
                **base,
                "path_found": result.get("path_found"),
                "paths_total": result.get("paths_total"),
                "paths": result.get("paths"),
                "source_ids": result.get("source_ids"),
                "target_ids": result.get("target_ids"),
            }
        )
    return walks
