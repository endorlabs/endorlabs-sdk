"""Multi-hop path search on decoded call-graph JSON."""

from __future__ import annotations

from collections import deque
from typing import Any

from endorlabs.workflows.callgraph.graph import (
    build_out_adjacency,
    build_uri_index,
    resolve_method_ids_by_patterns,
)

_DEFAULT_MAX_PATHS = 5


def _path_to_hops(path: list[int], uri_by_id: dict[int, str]) -> list[dict[str, Any]]:
    return [{"method_id": mid, "uri": uri_by_id.get(mid, "")} for mid in path]


def find_call_graph_path(
    callables: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    from_patterns: list[str],
    to_patterns: list[str],
    max_depth: int = 6,
    max_paths: int = _DEFAULT_MAX_PATHS,
) -> dict[str, Any]:
    """BFS shortest paths from *from_patterns* nodes to *to_patterns* nodes.

    Returns a stable JSON-serializable dict for CLI output and tests.
    """
    source_ids = resolve_method_ids_by_patterns(callables, from_patterns)
    target_ids = resolve_method_ids_by_patterns(callables, to_patterns)
    target_set = set(target_ids)
    uri_by_id = build_uri_index(callables)
    out_adj = build_out_adjacency(edges)

    empty: dict[str, Any] = {
        "from_pattern": from_patterns,
        "to_pattern": to_patterns,
        "max_depth": max_depth,
        "source_ids": source_ids,
        "target_ids": target_ids,
        "path_found": False,
        "paths": [],
        "paths_total": 0,
    }
    if not source_ids or not target_ids:
        return empty

    queue: deque[tuple[int, list[int]]] = deque((sid, [sid]) for sid in source_ids)
    found_paths: list[list[int]] = []
    shortest_len: int | None = None
    paths_total = 0

    while queue:
        node, path = queue.popleft()
        depth = len(path) - 1

        if node in target_set and depth > 0:
            paths_total += 1
            if shortest_len is None:
                shortest_len = depth
            if depth > shortest_len:
                break
            if depth == shortest_len:
                found_paths.append(path)
                if len(found_paths) >= max_paths:
                    break
            continue

        if depth >= max_depth:
            continue

        for nxt in out_adj.get(node, []):
            if nxt in path:
                continue
            queue.append((nxt, [*path, nxt]))

    hops = [_path_to_hops(p, uri_by_id) for p in found_paths]
    return {
        "from_pattern": from_patterns,
        "to_pattern": to_patterns,
        "max_depth": max_depth,
        "source_ids": source_ids,
        "target_ids": target_ids,
        "path_found": bool(found_paths),
        "paths": hops,
        "paths_total": paths_total,
    }
