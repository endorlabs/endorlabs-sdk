"""AI-SAST function_summary → Call Graph bridge workflow."""

from __future__ import annotations

from endorlabs.workflows.aisast_callgraph.join import (
    WALK_DISCLAIMER,
    clamp_walk_bounds,
    match_seeds_to_callables,
    patterns_from_seed,
    walk_from_matches,
)
from endorlabs.workflows.aisast_callgraph.precheck import (
    GATE_CG,
    GATE_RV,
    GATE_VECTOR,
    PrecheckResult,
    precheck_aisast_and_callgraph,
)
from endorlabs.workflows.aisast_callgraph.run import (
    AisastCallgraphBridgeResult,
    run_aisast_callgraph_bridge,
)
from endorlabs.workflows.aisast_callgraph.seeds import (
    ENTRY_POINT_QUERY,
    fetch_entry_point_seeds,
    parse_vector_match,
)
from endorlabs.workflows.aisast_callgraph.targets import (
    VulnWalkTarget,
    is_vuln_id_shaped,
    package_token_from_coordinate,
    path_patterns_for_package,
    resolve_vuln_walk_targets,
)

__all__ = [
    "ENTRY_POINT_QUERY",
    "GATE_CG",
    "GATE_RV",
    "GATE_VECTOR",
    "WALK_DISCLAIMER",
    "AisastCallgraphBridgeResult",
    "PrecheckResult",
    "VulnWalkTarget",
    "clamp_walk_bounds",
    "fetch_entry_point_seeds",
    "is_vuln_id_shaped",
    "match_seeds_to_callables",
    "package_token_from_coordinate",
    "parse_vector_match",
    "path_patterns_for_package",
    "patterns_from_seed",
    "precheck_aisast_and_callgraph",
    "resolve_vuln_walk_targets",
    "run_aisast_callgraph_bridge",
    "walk_from_matches",
]
