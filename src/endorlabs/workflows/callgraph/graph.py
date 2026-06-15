"""Shared call-graph graph utilities (URI index, adjacency, pattern resolution)."""

from __future__ import annotations

from typing import Any


def matches_all_patterns(text: str, patterns: list[str]) -> bool:
    """Return True when every pattern is a case-insensitive substring of *text*."""
    if not patterns:
        return True
    lowered = text.lower()
    return all(p.lower() in lowered for p in patterns)


def build_uri_index(callables: list[dict[str, Any]]) -> dict[int, str]:
    """Map method_id to URI for decoded callables rows."""
    return {int(row["method_id"]): str(row.get("uri", "")) for row in callables}


def build_out_adjacency(edges: list[dict[str, Any]]) -> dict[int, list[int]]:
    """Build forward adjacency source_id -> [target_id, ...]."""
    adj: dict[int, list[int]] = {}
    for edge in edges:
        src = int(edge["source_id"])
        tgt = int(edge["target_id"])
        adj.setdefault(src, []).append(tgt)
    return adj


def resolve_method_ids_by_patterns(
    callables: list[dict[str, Any]],
    patterns: list[str],
) -> list[int]:
    """Return method_ids whose URI matches all *patterns* (case-insensitive)."""
    if not patterns:
        return []
    return [
        int(row["method_id"])
        for row in callables
        if matches_all_patterns(str(row.get("uri", "")), patterns)
    ]
