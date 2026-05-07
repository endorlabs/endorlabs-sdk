"""URI normalization and stitched reachability helpers."""

from __future__ import annotations

from collections import deque
from typing import Any


def normalize_uri(uri: str) -> str:
    """Normalize call graph URI by dropping ecosystem/package prefix."""
    marker = uri.find("//")
    if marker == -1:
        return uri
    rest = uri[marker + 2 :]
    slash = rest.find("/")
    if slash == -1:
        return ""
    return rest[slash:]


def build_norm_index(callables: list[dict[str, Any]]) -> dict[str, set[int]]:
    """Build normalized URI -> method IDs index."""
    idx: dict[str, set[int]] = {}
    for row in callables:
        mid = row.get("method_id")
        if not isinstance(mid, int):
            continue
        n = normalize_uri(str(row.get("uri", "")))
        idx.setdefault(n, set()).add(mid)
    return idx


def build_adjacency(edges: list[dict[str, Any]]) -> dict[int, list[int]]:
    """Build source->target adjacency list from decoded edges."""
    adj: dict[int, list[int]] = {}
    for row in edges:
        src = row.get("source_id")
        tgt = row.get("target_id")
        if not isinstance(src, int) or not isinstance(tgt, int):
            continue
        adj.setdefault(src, []).append(tgt)
    return adj


def find_bridge_norms(
    customer_callables: list[dict[str, Any]],
    oss_callables: list[dict[str, Any]],
    *,
    allowed_prefixes: tuple[str, ...] | None = None,
) -> set[str]:
    """Find shared normalized method URIs between customer and OSS graphs."""
    c_idx = build_norm_index(customer_callables)
    o_idx = build_norm_index(oss_callables)
    shared = set(c_idx).intersection(set(o_idx))
    if allowed_prefixes:
        shared = {n for n in shared if n.startswith(allowed_prefixes)}
    return shared


def bfs_multi_source(
    starts: list[int],
    adjacency: dict[int, list[int]],
    targets: set[int],
) -> dict[int, int | None]:
    """Run multi-source BFS and return predecessor map."""
    q = deque(starts)
    prev: dict[int, int | None] = {s: None for s in starts}
    seen = set(starts)
    found = set()
    while q and found != targets:
        cur = q.popleft()
        if cur in targets:
            found.add(cur)
        for nxt in adjacency.get(cur, []):
            if nxt in seen:
                continue
            seen.add(nxt)
            prev[nxt] = cur
            q.append(nxt)
    return prev


def reconstruct_path(prev: dict[int, int | None], target: int) -> list[int] | None:
    """Reconstruct BFS path if target is reachable."""
    if target not in prev:
        return None
    out: list[int] = []
    cur: int | None = target
    while cur is not None:
        out.append(cur)
        cur = prev.get(cur)
    out.reverse()
    return out
