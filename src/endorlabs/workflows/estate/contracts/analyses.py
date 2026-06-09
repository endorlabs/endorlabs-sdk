"""Estate analysis registry — disk-only transforms and required layers."""

from __future__ import annotations

from dataclasses import dataclass

ANALYSIS_VERSION_CARDINALITY = "version_cardinality"
ANALYSIS_RISK_CARDINALITY = "risk_cardinality"
ANALYSIS_FAMILY_RISK_CHART = "family_risk_chart"
ANALYSIS_COMPILE_DEPENDENCY_GRAPH = "compile_dependency_graph"
ANALYSIS_GRAPH_ENRICH = "graph_enrich"
ANALYSIS_GRAPH_METRICS = "graph_metrics"
ANALYSIS_PROJECT_RELATIONSHIP_MAP = "project_relationship_map"

AnalysisStatus = str  # pending | complete | failed


@dataclass(frozen=True, slots=True)
class AnalysisSpec:
    """Declares layer dependencies for one analysis kind."""

    analysis_id: str
    required_layers: tuple[str, ...]
    optional_layers: tuple[str, ...]
    output_subdir: str


ANALYSIS_REGISTRY: dict[str, AnalysisSpec] = {
    ANALYSIS_VERSION_CARDINALITY: AnalysisSpec(
        analysis_id=ANALYSIS_VERSION_CARDINALITY,
        required_layers=(),
        optional_layers=("dependency_corpus", "grouped_dm_index"),
        output_subdir="version_cardinality",
    ),
    ANALYSIS_RISK_CARDINALITY: AnalysisSpec(
        analysis_id=ANALYSIS_RISK_CARDINALITY,
        required_layers=("findings_sca_vulnerability_main",),
        optional_layers=("dependency_corpus",),
        output_subdir="risk_cardinality",
    ),
    ANALYSIS_FAMILY_RISK_CHART: AnalysisSpec(
        analysis_id=ANALYSIS_FAMILY_RISK_CHART,
        required_layers=(),
        optional_layers=(
            "findings_sca_vulnerability_main",
            "dependency_corpus",
        ),
        output_subdir="family_risk_chart",
    ),
    ANALYSIS_COMPILE_DEPENDENCY_GRAPH: AnalysisSpec(
        analysis_id=ANALYSIS_COMPILE_DEPENDENCY_GRAPH,
        required_layers=("dependency_corpus", "publisher_index"),
        optional_layers=("projects",),
        output_subdir="compile_graph",
    ),
    ANALYSIS_GRAPH_ENRICH: AnalysisSpec(
        analysis_id=ANALYSIS_GRAPH_ENRICH,
        required_layers=("compile_dependency_graph",),
        optional_layers=("findings_sca_vulnerability_main",),
        output_subdir="graph_enrich",
    ),
    ANALYSIS_GRAPH_METRICS: AnalysisSpec(
        analysis_id=ANALYSIS_GRAPH_METRICS,
        required_layers=("compile_dependency_graph",),
        optional_layers=(),
        output_subdir="graph_metrics",
    ),
    ANALYSIS_PROJECT_RELATIONSHIP_MAP: AnalysisSpec(
        analysis_id=ANALYSIS_PROJECT_RELATIONSHIP_MAP,
        required_layers=("dependency_corpus", "projects"),
        optional_layers=(),
        output_subdir="project_map",
    ),
}


def analysis_output_relpath(analysis_id: str) -> str:
    spec = ANALYSIS_REGISTRY.get(analysis_id)
    if spec is None:
        msg = f"Unknown analysis id {analysis_id!r}"
        raise ValueError(msg)
    return f"analyses/{spec.output_subdir}"
