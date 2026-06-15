"""Call graph export, search, path, and manifest utilities."""

from __future__ import annotations

from .export import run_callgraph_export
from .graph import (
    build_out_adjacency,
    build_uri_index,
    matches_all_patterns,
    resolve_method_ids_by_patterns,
)
from .manifest import resolve_callgraph_export_artifact
from .path import find_call_graph_path
from .path_cli import run_path_search
from .resolve import (
    build_callgraph_pv_inventory,
    list_package_versions_for_project,
    order_pvs_for_callgraph,
    project_as_list_source,
    pv_call_graph_available,
    resolve_package_version_with_callgraph,
)
from .search import parse_search_args, run_search_main, search_decoded_call_graph

__all__ = [
    "build_callgraph_pv_inventory",
    "build_out_adjacency",
    "build_uri_index",
    "find_call_graph_path",
    "list_package_versions_for_project",
    "matches_all_patterns",
    "order_pvs_for_callgraph",
    "parse_search_args",
    "project_as_list_source",
    "pv_call_graph_available",
    "resolve_callgraph_export_artifact",
    "resolve_method_ids_by_patterns",
    "resolve_package_version_with_callgraph",
    "run_callgraph_export",
    "run_path_search",
    "run_search_main",
    "search_decoded_call_graph",
]
