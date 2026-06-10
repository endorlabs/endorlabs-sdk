"""BOM graph extraction and slim dependency row shaping."""

from __future__ import annotations

from collections import deque
from typing import Any

from endorlabs.workflows.dependencies.coordinates import parse_dep_name


def _bom_to_serializable(bom: Any) -> dict[str, Any]:
    """Convert a BOM (model or dict) to a plain serializable dict."""
    if isinstance(bom, dict):
        return bom
    if hasattr(bom, "model_dump"):
        return bom.model_dump(mode="json", warnings=False)
    return {"raw": str(bom)}


def retrieve_bom_full(pv: Any) -> dict[str, Any]:
    """Extract the full BOM from a PackageVersion as a serializable dict."""
    bom = pv.spec.resolved_dependencies if pv.spec else None
    if bom is None:
        return {}
    return _bom_to_serializable(bom)


def _normalize_children(children_raw: list[Any]) -> list[str]:
    """Normalize BOM graph children to a list of string keys."""
    children: list[str] = []
    if not children_raw:
        return children
    for c in children_raw:
        if isinstance(c, str):
            children.append(c)
        elif isinstance(c, dict):
            children.append(c.get("name", c.get("key", str(c))))
        else:
            children.append(str(c))
    return children


def count_transitive_children(graph: dict[str, Any], root: str) -> int:
    """BFS from *root*, return count of unique transitive descendants."""
    visited: set[str] = set()
    queue = deque(_normalize_children(graph.get(root, [])))
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        queue.extend(
            c for c in _normalize_children(graph.get(node, [])) if c not in visited
        )
    return len(visited)


def extract_direct_deps(graph: dict[str, Any]) -> list[tuple[str, str, int]]:
    """Find direct dependencies from a BOM adjacency-list graph.

    Returns ``[(full_name, version, transitive_child_count), ...]``.
    """
    all_children: set[str] = set()
    for children_raw in graph.values():
        if isinstance(children_raw, list):
            all_children.update(_normalize_children(children_raw))

    roots = [k for k in graph if k not in all_children]
    if not roots:
        roots = list(graph.keys())[:3]

    direct_dep_names: list[str] = []
    for root in roots:
        direct_dep_names.extend(_normalize_children(graph.get(root, [])))

    seen: set[str] = set()
    unique_directs: list[str] = []
    for d in direct_dep_names:
        if d not in seen:
            seen.add(d)
            unique_directs.append(d)

    result: list[tuple[str, str, int]] = []
    for dep in sorted(unique_directs):
        name, ver = parse_dep_name(dep)
        result.append((name, ver, count_transitive_children(graph, dep)))
    return result


def render_slim_dependencies(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Transform raw DependencyMetadata rows into slim dicts."""
    slim: list[dict[str, Any]] = []
    for row in rows:
        spec = row.get("spec", {}) or {}
        dd = spec.get("dependency_data", {}) or {}
        reach_raw = str(dd.get("reachable", "") or dd.get("reachability", ""))
        if "UNREACHABLE" in reach_raw:
            reachable: bool | None = False
        elif "REACHABLE" in reach_raw:
            reachable = True
        else:
            reachable = None
        slim.append(
            {
                "name": dd.get("package_name", "") or "",
                "version": (
                    dd.get("resolved_version", "")
                    or dd.get("unresolved_version", "")
                    or ""
                ),
                "direct": dd.get("direct", False),
                "reachable": reachable,
                "ecosystem": (dd.get("ecosystem", "") or "")
                .replace("ECOSYSTEM_", "")
                .lower(),
                "scope": (dd.get("scope", "") or "")
                .replace("DEPENDENCY_SCOPE_", "")
                .lower(),
            }
        )
    return slim
