"""Call graph artifact helpers — thin re-export.

Prefer ``endorlabs.tools.callgraph_artifacts`` in new code.
Wire decode stays on ``client.CallGraphData``.
"""

from __future__ import annotations

from endorlabs.tools.callgraph_artifacts import (
    generate_call_graph_analysis_md,
    render_call_graph_summary_md,
    summarize_call_graph,
)

__all__ = [
    "generate_call_graph_analysis_md",
    "render_call_graph_summary_md",
    "summarize_call_graph",
]
