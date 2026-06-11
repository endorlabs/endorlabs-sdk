"""Backward-compatible re-exports for split dependency/call-graph workflow modules.

Canonical import paths:

- ``endorlabs.utils.artifact_io`` — ``slugify``, ``write_json``
- ``endorlabs.workflows.dependencies.coordinates`` — ``parse_dep_name``
- ``endorlabs.workflows.dependencies.bom_graph`` — BOM graph helpers
- ``endorlabs.workflows.dependencies.metadata_fetch`` — DependencyMetadata fetch
- ``endorlabs.workflows.callgraph.proto_decode`` — protobuf decode types/helpers
- ``endorlabs.workflows.callgraph.render`` — Markdown rendering
- ``endorlabs.workflows.callgraph.fetch`` — summary artifact helpers
- ``client.CallGraphData.decode`` / ``fetch`` — call graph fetch + decode
- ``endorlabs.workflows.agent_context.hydration`` — per-project hydration
"""

from __future__ import annotations

from endorlabs.utils.artifact_io import slugify, write_json
from endorlabs.workflows.agent_context.hydration import (
    ProjectResult,
    PVResult,
    build_dependency_callgraph_summary,
    process_project,
)
from endorlabs.workflows.callgraph.fetch import (
    generate_call_graph_analysis_md,
    render_call_graph_summary_md,
    summarize_call_graph,
)
from endorlabs.workflows.callgraph.proto_decode import (
    _HAS_ZSTD,
    CallableInfo,
    CallEdge,
    CallGraphInfo,
    CallSiteInfo,
    TypeInfo,
    decode_callgraph,
)
from endorlabs.workflows.callgraph.render import (
    build_call_tree,
    render_callgraph_analysis,
)
from endorlabs.workflows.dependencies.bom_graph import (
    count_transitive_children,
    extract_direct_deps,
    render_slim_dependencies,
    retrieve_bom_full,
)
from endorlabs.workflows.dependencies.coordinates import parse_dep_name
from endorlabs.workflows.dependencies.metadata_fetch import (
    retrieve_dep_metadata_full,
    summarize_dep_metadata,
)

__all__ = [
    "_HAS_ZSTD",
    "CallEdge",
    "CallGraphInfo",
    "CallSiteInfo",
    "CallableInfo",
    "PVResult",
    "ProjectResult",
    "TypeInfo",
    "build_call_tree",
    "build_dependency_callgraph_summary",
    "count_transitive_children",
    "decode_callgraph",
    "extract_direct_deps",
    "generate_call_graph_analysis_md",
    "parse_dep_name",
    "process_project",
    "render_call_graph_summary_md",
    "render_callgraph_analysis",
    "render_slim_dependencies",
    "retrieve_bom_full",
    "retrieve_dep_metadata_full",
    "slugify",
    "summarize_call_graph",
    "summarize_dep_metadata",
    "write_json",
]
