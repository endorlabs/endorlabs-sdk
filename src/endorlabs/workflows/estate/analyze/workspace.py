"""Disk-first estate workspace analysis orchestrator."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from endorlabs.tools.dependency_explorer import write_json
from endorlabs.workflows.estate.analyze.compile_graph.disk_build import (
    run_graph_pipeline_from_workspace,
)
from endorlabs.workflows.estate.analyze.risk.cardinality import (
    analyze_risk_cardinality_from_workspace,
)
from endorlabs.workflows.estate.collect.dependency_metadata import (
    load_dependency_metadata_records,
    rollup_version_cardinality,
)
from endorlabs.workflows.estate.export.charts.estate_dashboard import (
    export_estate_dashboard,
)
from endorlabs.workflows.estate.workspace.collect_manifest import (
    validate_workspace_collect,
)
from endorlabs.workflows.estate.workspace.paths import (
    ensure_workspace_layout,
    ir_dir,
    ir_path,
)

logger = logging.getLogger(__name__)

AnalysisStep = Literal["cardinality", "risk", "graph", "viz", "relationships"]


@dataclass(frozen=True, slots=True)
class AnalyzeResult:
    workspace_root: Path
    steps: dict[str, str]


def _write_version_cardinality_ir(workspace_root: Path, namespace: str) -> int:
    records = load_dependency_metadata_records(workspace_root)
    rows = rollup_version_cardinality(records, namespace)
    payload = {
        "schema": "endor.version_cardinality.v1",
        "estate_root": namespace,
        "generated_at": _utc_now(),
        "package_count": len(rows),
        "packages": rows,
    }
    write_json(
        str(ir_path(workspace_root, "version_cardinality.json")),
        payload,
        base_dir=workspace_root,
    )
    return len(rows)


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def analyze_workspace(
    workspace_root: Path,
    *,
    namespace: str,
    only: tuple[AnalysisStep, ...] | None = None,
    top_n: int = 20,
    scorer: str = "critical_high_count",
    skip_metrics: bool = False,
    skip_validate: bool = False,
    relationship_max_depth: int = 3,
    relationship_max_workers: int = 16,
) -> AnalyzeResult:
    """Run disk-first IR transforms and unified viz from pulled workspace data."""
    ensure_workspace_layout(workspace_root)
    steps = only or ("cardinality", "risk", "graph", "viz")
    disk_steps = frozenset({"cardinality", "risk", "graph", "viz"})
    if not skip_validate and disk_steps.intersection(steps):
        validate_workspace_collect(workspace_root)

    outcomes: dict[str, str] = {}

    if "cardinality" in steps:
        count = _write_version_cardinality_ir(workspace_root, namespace)
        outcomes["cardinality"] = f"{count} packages"

    if "risk" in steps:
        result = analyze_risk_cardinality_from_workspace(
            workspace_root,
            namespace,
            top_n=top_n,
            scorer=scorer,
        )
        outcomes["risk"] = result.message

    if "graph" in steps:
        run_graph_pipeline_from_workspace(
            workspace_root,
            namespace=namespace,
            skip_metrics=skip_metrics,
        )
        outcomes["graph"] = "compile graph IR complete"

    if "viz" in steps:
        dashboard = export_estate_dashboard(
            workspace_root,
            namespace_label=namespace,
            top_n=top_n,
            scorer_name=scorer,
        )
        outcomes["viz"] = str(dashboard)

    if "relationships" in steps:
        import endorlabs
        from endorlabs.workflows.estate.analyze.project_map.run import (
            run_project_relationship_map,
        )

        client = endorlabs.Client(tenant=namespace)
        try:
            rel_result = run_project_relationship_map(
                client,
                namespace=namespace,
                output_dir=ir_dir(workspace_root),
                max_depth=relationship_max_depth,
                max_workers=relationship_max_workers,
            )
        finally:
            client.close()
        direct = rel_result.stats.get("direct_project_edge_count", 0)
        outcomes["relationships"] = (
            f"{direct} direct edges -> {rel_result.graph_path.name}"
        )

    return AnalyzeResult(workspace_root=workspace_root, steps=outcomes)
