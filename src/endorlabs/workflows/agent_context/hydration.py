"""Per-project BOM, DependencyMetadata, and call-graph hydration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

from endorlabs.core.exceptions import NotFoundError
from endorlabs.tools.callgraph_artifacts import (
    generate_call_graph_analysis_md,
    render_call_graph_summary_md,
    summarize_call_graph,
)
from endorlabs.tools.dependency_metadata import (
    retrieve_dep_metadata_full,
    summarize_dep_metadata,
)
from endorlabs.utils.artifact_io import slugify, write_json
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.dependencies.bom_graph import (
    extract_direct_deps,
    render_slim_dependencies,
    retrieve_bom_full,
)

if TYPE_CHECKING:
    from endorlabs import Client

logger = get_resource_logger(__name__)


@dataclass
class PVResult:
    """Per-PackageVersion retrieval results."""

    pv_name: str = ""
    pv_uuid: str = ""
    pv_slug: str = ""
    cg_available: bool = False
    bom_file: str = ""
    cg_file: str = ""
    cg_analysis_file: str = ""
    deps_file: str = ""
    bom_summary: dict[str, Any] = field(default_factory=dict)
    cg_summary: dict[str, Any] = field(default_factory=dict)
    direct_deps: list[tuple[str, str, int]] = field(default_factory=list)
    graph_nodes: int = 0


@dataclass
class ProjectResult:
    """Full retrieval results for one project."""

    project_uuid: str = ""
    project_name: str = ""
    namespace: str = ""
    slug: str = ""
    out_dir: str = ""
    pv_results: list[PVResult] = field(default_factory=list)
    dep_metadata_stats: dict[str, Any] = field(default_factory=dict)
    dep_metadata_namespace: str = ""
    dep_metadata_count: int = 0
    dep_metadata_truncated: bool = False
    report: str = ""
    pv_list_truncated: bool = False
    hydration_missing_pv_uuids: list[str] = field(default_factory=list)


def process_project(
    client: Client,
    root_namespace: str,
    project: Any,
    out_dir: str,
    pv_limit: int = 5,
    dep_metadata_max_pages: int = 0,
    *,
    deterministic: bool = False,
    pv_uuid_order: list[str] | None = None,
    pv_list_max_pages: int = 50,
    pv_list_page_size: int = 200,
) -> ProjectResult:
    """Retrieve full dependency tree and call graph data for one project.

    Args:
        client: Authenticated Endor Labs Client.
        root_namespace: Tenant namespace.
        project: Project resource object.
        out_dir: Output directory for this project's artifacts.
        pv_limit: Maximum PackageVersions to process.
        dep_metadata_max_pages: Max pages for DependencyMetadata pagination.
        deterministic: When True, sort package versions and dependency rows
            so output artifacts are stable across runs.
        pv_uuid_order: When set, list with broader pagination then hydrate only
            these UUIDs (in order), after applying *pv_limit* to that sequence.
        pv_list_max_pages: Max list pages when resolving *pv_uuid_order*.
        pv_list_page_size: List page size when resolving *pv_uuid_order*.

    Returns:
        :class:`ProjectResult` with paths to all written artifacts.
    """
    project_name = project.meta.name if project.meta else project.uuid
    project_ns = (
        project.tenant_meta.namespace
        if project.tenant_meta and project.tenant_meta.namespace
        else root_namespace
    )
    slug = slugify(project_name)
    os.makedirs(out_dir, exist_ok=True)

    result = ProjectResult(
        project_uuid=project.uuid,
        project_name=project_name,
        namespace=project_ns,
        slug=slug,
        out_dir=out_dir,
    )

    # 1. PackageVersions
    logger.info("  Fetching PackageVersions ...")
    missing: list[str] = []
    if pv_uuid_order:
        pvs_full = client.PackageVersion.list_by_project(
            project,
            namespace=project_ns,
            max_pages=pv_list_max_pages,
            page_size=pv_list_page_size,
        )
        listed_cap = pv_list_max_pages * pv_list_page_size
        result.pv_list_truncated = len(pvs_full) >= listed_cap
        by_uuid = {pv.uuid: pv for pv in pvs_full if getattr(pv, "uuid", None)}
        ordered: list[Any] = []
        for uid in pv_uuid_order:
            if uid in by_uuid:
                ordered.append(by_uuid[uid])
            else:
                missing.append(uid)
        if missing:
            logger.warning(
                "  Package versions not found in list results (first 10): %s",
                missing[:10],
            )
        pvs = ordered
        if pv_limit and pv_limit > 0:
            pvs = pvs[:pv_limit]
    else:
        pvs = client.PackageVersion.list_by_project(
            project,
            namespace=project_ns,
            max_pages=1,
            page_size=pv_limit,
        )
        pvs = pvs[:pv_limit]
        if deterministic:
            pvs = sorted(pvs, key=lambda pv: str(pv.meta.name if pv.meta else pv.uuid))
    result.hydration_missing_pv_uuids = missing
    single_pv = len(pvs) == 1

    # 2. Per-PV: BOM + Call Graph
    for pv in pvs:
        pv_name = pv.meta.name if pv.meta else pv.uuid
        pv_slug = slugify(pv_name, max_len=60)
        cg_available = bool(pv.spec and pv.spec.call_graph_available)

        pvr = PVResult(
            pv_name=pv_name,
            pv_uuid=pv.uuid,
            pv_slug=pv_slug,
            cg_available=cg_available,
        )

        # BOM
        bom_data = retrieve_bom_full(pv)
        if bom_data:
            bom_filename = "bom.json" if single_pv else f"bom_{pv_slug}.json"
            bom_path = os.path.join(out_dir, bom_filename)
            write_json(bom_path, bom_data, base_dir=Path(out_dir))
            pvr.bom_file = bom_path
            graph = bom_data.get("dependency_graph", {}) or {}
            pvr.graph_nodes = len(graph)
            pvr.direct_deps = extract_direct_deps(graph)
            pvr.bom_summary = {
                "graph_nodes": len(graph),
                "dependency_count": len(bom_data.get("dependencies", []) or []),
            }

        # Call Graph
        logger.info("  [CallGraph] %s (available=%s)", pv_name, cg_available)
        try:
            cg_data = client.CallGraphData.fetch(pv)
        except NotFoundError:
            cg_data = {}
        if cg_data:
            cg_filename = (
                "call_graph.json" if single_pv else f"call_graph_{pv_slug}.json"
            )
            cg_path = os.path.join(out_dir, cg_filename)
            write_json(cg_path, cg_data, base_dir=Path(out_dir))
            pvr.cg_file = cg_path
            pvr.cg_summary = summarize_call_graph(cg_data)
            analysis_path = generate_call_graph_analysis_md(cg_path)
            if analysis_path:
                pvr.cg_analysis_file = analysis_path

        result.pv_results.append(pvr)

    # 3. DependencyMetadata
    logger.info("  [DepMetadata] project_uuid=%s", project.uuid)
    dep_rows, dep_ns, dep_truncated = retrieve_dep_metadata_full(
        client,
        project_ns,
        project.uuid,
        max_pages=dep_metadata_max_pages,
    )
    result.dep_metadata_truncated = dep_truncated
    if dep_truncated:
        logger.warning(
            "  DependencyMetadata list truncated for project %s "
            "(dep_metadata_max_pages=%s); use 0 for unlimited",
            project.uuid,
            dep_metadata_max_pages,
        )
    if deterministic:
        dep_rows = sorted(
            dep_rows,
            key=lambda row: (
                str(row.get("tenant_meta", {}).get("namespace", "")),
                str(
                    row.get("spec", {})
                    .get("dependency_data", {})
                    .get("package_name", "")
                ),
                str(
                    row.get("spec", {})
                    .get("dependency_data", {})
                    .get("resolved_version", "")
                ),
            ),
        )
    result.dep_metadata_count = len(dep_rows)
    result.dep_metadata_namespace = dep_ns
    out_base = Path(out_dir)
    if dep_rows:
        write_json(
            os.path.join(out_dir, "dep_metadata.json"),
            dep_rows,
            base_dir=out_base,
        )
        result.dep_metadata_stats = summarize_dep_metadata(dep_rows)
        slim = render_slim_dependencies(dep_rows)
        write_json(
            os.path.join(out_dir, "dependencies.json"),
            slim,
            base_dir=out_base,
        )

    # 4. Build summary
    result.report = build_dependency_callgraph_summary(result)
    return result


# ===================================================================
#  Section 10 — Markdown summary builders
# ===================================================================


def _render_pv_section(pv: PVResult, heading_level: str, buf: StringIO) -> None:
    """Render one PV's Dependencies + Call Graph into the Markdown buffer."""
    dep_count = max(pv.graph_nodes - 1, 0)
    direct_count = len(pv.direct_deps)
    transitive_count = dep_count - direct_count if dep_count > direct_count else 0

    buf.write(
        f"{heading_level} Dependencies"
        f" \u2014 {dep_count} total"
        f" ({direct_count} direct, {transitive_count} transitive)\n\n"
    )
    if pv.direct_deps:
        buf.write("| Direct Dependency | Version | Transitive Children |\n")
        buf.write("|-------------------|---------|---------------------|\n")
        buf.writelines(
            f"| {name} | {ver} | {trans} |\n" for name, ver, trans in pv.direct_deps
        )
        buf.write("\n")

    bom_fn = os.path.basename(pv.bom_file) if pv.bom_file else None
    if bom_fn:
        buf.write(f"> Full graph: [`{bom_fn}`]({bom_fn}) ({pv.graph_nodes} nodes)\n")
    buf.write("\n")

    if pv.cg_available or pv.cg_file:
        buf.write(f"{heading_level} Call Graph\n\n")
        cg_fn = os.path.basename(pv.cg_file) if pv.cg_file else None
        cg_analysis_fn = (
            os.path.basename(pv.cg_analysis_file) if pv.cg_analysis_file else None
        )
        cg_md: str | None = None
        if pv.cg_file and os.path.isfile(pv.cg_file):
            cg_md = render_call_graph_summary_md(pv.cg_file)
        if cg_md:
            buf.write(cg_md)
            buf.write("\n\n")
        else:
            uuid_val = pv.cg_summary.get("uuid", "n/a")
            fmt = pv.cg_summary.get("call_graph_format", "unknown")
            buf.write(f"UUID: `{uuid_val}` | Format: {fmt}\n\n")
        if cg_analysis_fn:
            buf.write(f"> Decoded analysis: [`{cg_analysis_fn}`]({cg_analysis_fn})  \n")
        if cg_fn:
            buf.write(f"> Raw data: [`{cg_fn}`]({cg_fn})\n")
        buf.write("\n")


def build_dependency_callgraph_summary(result: ProjectResult) -> str:
    """Build the ``dependency-callgraph-summary.md`` content.

    This is the renamed equivalent of the old ``README.md`` / ``summary.txt``.
    """
    buf = StringIO()
    single_pv = len(result.pv_results) == 1

    if single_pv and result.pv_results:
        buf.write(f"# {result.pv_results[0].pv_name}\n\n")
    else:
        buf.write(f"# {result.project_name}\n\n")

    buf.write("| | |\n|---|---|\n")
    buf.write(f"| Repository | {result.project_name} |\n")
    buf.write(f"| Project UUID | `{result.project_uuid}` |\n")
    buf.write(f"| Namespace | `{result.namespace}` |\n\n")

    if not single_pv and result.pv_results:
        buf.write(f"## Package Versions ({len(result.pv_results)})\n\n")
        buf.write("| # | Package Version | Dependencies | Call Graph | BOM File |\n")
        buf.write("|---|----------------|--------------|------------|----------|\n")
        for i, pvr in enumerate(result.pv_results, 1):
            bom_fn = os.path.basename(pvr.bom_file) if pvr.bom_file else "-"
            cg_yn = "Yes" if (pvr.cg_available or pvr.cg_file) else "No"
            dep_count = max(pvr.graph_nodes - 1, 0)
            buf.write(f"| {i} | {pvr.pv_name} | {dep_count} | {cg_yn} | `{bom_fn}` |\n")
        buf.write("\n")

    for i, pvr in enumerate(result.pv_results, 1):
        if single_pv:
            heading = "##"
        else:
            buf.write(f"---\n\n### {i}. {pvr.pv_name}\n\n")
            heading = "####"
        _render_pv_section(pvr, heading, buf)

    stats = result.dep_metadata_stats
    if stats:
        if not single_pv:
            buf.write("---\n\n")
        buf.write("## Dependency Metadata (project-level)\n\n")
        total = stats.get("total", 0)
        direct = stats.get("direct", 0)
        trans = stats.get("transitive", 0)
        reach = stats.get("reachable", 0)
        unreach = stats.get("unreachable", 0)
        unknown = stats.get("unknown_reachability", 0)
        ecos = stats.get("by_ecosystem", {})
        eco_parts = [
            f"{k.replace('ECOSYSTEM_', '')}: {v}" for k, v in sorted(ecos.items())
        ]
        buf.write(f"- **Total**: {total} ({direct} direct, {trans} transitive)\n")
        buf.write(
            f"- **Reachability**: {reach} reachable, "
            f"{unreach} unreachable, {unknown} unknown\n"
        )
        if eco_parts:
            buf.write(f"- **Ecosystems**: {', '.join(eco_parts)}\n")
        buf.write("\n")

    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    buf.write(f"---\n\n*Generated at {ts}*\n")
    return buf.getvalue()
