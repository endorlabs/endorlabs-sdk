#!/usr/bin/env python3
"""Export a machine-readable project context bundle for agent workflows.

Includes BOM, DependencyMetadata, and optional call graph sweep.

Multi-pass retrieval:
  Pass 1 — optional wide ``package_versions_index.json`` (bounded list).
  Pass 2 — ``process_project`` hydration (default first *pv_limit* PVs, or
  selected UUIDs / top-N).
  Pass 3 — optional ``--callgraph-sweep`` over listed package versions.

Writes ``context_manifest.json`` and ``dependency-callgraph-summary.md`` under
``<output_dir>/<slug>_<timestamp>/``.
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.context.paths import workflow_projects_root
from endorlabs.tools.dependency_explorer import (
    ProjectResult,
    process_project,
    slugify,
    write_json,
)
from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.agent_context.package_versions import (
    build_index_rows,
    list_package_versions_for_index,
    parse_uuid_list_csv,
    select_top_n_uuids_by_update_time,
)
from endorlabs.workflows.callgraph.sweep import run_callgraph_sweep
from endorlabs.workflows.projects.resolve import resolve_project

LOGGER = logging.getLogger(__name__)
MANIFEST_VERSION = 2


def _write_text(base: Path, path: Path, content: str) -> None:
    safe_write_text(base, path, content)


def build_context_manifest(
    *,
    version: int,
    tenant: str,
    project_uuid: str,
    project_name: str,
    project_namespace: str,
    cli: dict[str, Any],
    warnings: list[str],
    project_result: ProjectResult,
    out_dir: Path,
    callgraph_sweep: dict[str, Any] | None,
    inventory: dict[str, Any] | None,
    selection: dict[str, Any] | None,
    hydration: dict[str, Any] | None,
) -> dict[str, Any]:
    """Assemble the context manifest dict (for JSON serialization)."""
    pvs_out: list[dict[str, Any]] = [
        {
            "pv_uuid": pvr.pv_uuid,
            "pv_name": pvr.pv_name,
            "bom_file": pvr.bom_file or None,
            "call_graph_file": pvr.cg_file or None,
            "call_graph_analysis_md": pvr.cg_analysis_file or None,
            "cg_available_flag": pvr.cg_available,
        }
        for pvr in project_result.pv_results
    ]

    dmeta = out_dir / "dep_metadata.json"
    djs = out_dir / "dependencies.json"
    idx_path = out_dir / "package_versions_index.json"
    artifacts: dict[str, Any] = {
        "dependency_callgraph_summary_md": str(
            out_dir / "dependency-callgraph-summary.md"
        ),
        "dep_metadata_json": str(dmeta) if dmeta.is_file() else None,
        "dependencies_slim_json": str(djs) if djs.is_file() else None,
        "package_versions_index_json": str(idx_path) if idx_path.is_file() else None,
        "package_version_artifacts": pvs_out,
        "dep_metadata_list_namespace": project_result.dep_metadata_namespace or None,
        "dep_metadata_row_count": project_result.dep_metadata_count,
        "dep_metadata_truncated": project_result.dep_metadata_truncated,
    }
    artifacts["callgraph_sweep"] = callgraph_sweep

    out: dict[str, Any] = {
        "version": version,
        "generated_at": datetime.now(UTC).isoformat() + "Z",
        "subject": {
            "root_tenant": tenant,
            "project_uuid": project_uuid,
            "project_name": project_name,
            "namespace": project_namespace,
        },
        "cli": cli,
        "warnings": warnings,
        "dependency_explorer": {
            "pv_limit": cli.get("pv_limit"),
            "dep_metadata_max_pages": cli.get("dep_metadata_max_pages"),
        },
        "artifacts": artifacts,
    }
    if inventory is not None:
        out["inventory"] = inventory
    if selection is not None:
        out["selection"] = selection
    if hydration is not None:
        out["hydration"] = hydration
    return out


def parse_args() -> argparse.Namespace:
    """Build argparse parser for this workflow CLI."""
    p = argparse.ArgumentParser(
        description=(
            "Export project dependency + call graph context for agent workflows."
        )
    )
    p.add_argument(
        "--tenant",
        required=True,
        help="Client tenant (auth context), e.g. endor from ENDOR_NAMESPACE root.",
    )
    p.add_argument(
        "--namespace",
        default="",
        help="Namespace for initial project resolution (default: --tenant).",
    )
    p.add_argument(
        "--project",
        required=True,
        help="Project UUID (24-hex) or exact project name (e.g. repository URL).",
    )
    p.add_argument(
        "--output-dir",
        default=str(workflow_projects_root()),
        help="Base output directory. Default: .endorlabs-context/workspace/projects",
    )
    p.add_argument(
        "--pv-limit",
        type=int,
        default=5,
        help="Max package versions to hydrate in Pass 2 (legacy list or cap on "
        "selected UUIDs). Default: 5",
    )
    p.add_argument(
        "--dep-metadata-max-pages",
        type=int,
        default=0,
        help="Max pages of DependencyMetadata to fetch (0 = unlimited).",
    )
    p.add_argument(
        "--deterministic",
        action="store_true",
        help="Sort PVs and dependency rows for stable outputs (legacy list mode).",
    )
    p.add_argument(
        "--no-pv-index",
        dest="pv_index",
        action="store_false",
        help=(
            "Skip Pass 1 package_versions_index.json "
            "(faster; disables --hydrate-top-n)."
        ),
    )
    p.set_defaults(pv_index=True)
    p.add_argument(
        "--pv-index-max-pages",
        type=int,
        default=50,
        help="Pass 1: max pages for PackageVersion.list. Default: 50",
    )
    p.add_argument(
        "--pv-index-page-size",
        type=int,
        default=200,
        help="Pass 1: page size for index list. Default: 200",
    )
    p.add_argument(
        "--index-only",
        action="store_true",
        help="Pass 1 only: write index + manifest; skip BOM/call graph hydration.",
    )
    p.add_argument(
        "--hydrate-pv-uuids",
        default="",
        help="Comma-separated PV UUIDs to hydrate in Pass 2 (implies broader list).",
    )
    p.add_argument(
        "--hydrate-top-n",
        type=int,
        default=0,
        help=(
            "Hydrate top N package versions by meta_update_time "
            "(requires Pass 1 index)."
        ),
    )
    p.add_argument(
        "--pv-list-max-pages",
        type=int,
        default=50,
        help=(
            "When resolving selected UUIDs: max pages for PackageVersion.list. "
            "Default: 50"
        ),
    )
    p.add_argument(
        "--pv-list-page-size",
        type=int,
        default=200,
        help="When resolving selected UUIDs: list page size. Default: 200",
    )
    p.add_argument(
        "--callgraph-sweep",
        action="store_true",
        help="Pass 3: list package versions and export call graph payloads.",
    )
    p.add_argument(
        "--callgraph-max-pages",
        type=int,
        default=50,
        help="Pass 3: max pages for PackageVersion listing. Default: 50",
    )
    p.add_argument(
        "--callgraph-page-size",
        type=int,
        default=200,
        help="Pass 3: page size for call graph sweep. Default: 200",
    )
    p.add_argument(
        "--decode-zstd",
        action="store_true",
        help=(
            "With --callgraph-sweep, decode zstd and emit decoded callables/edges JSON."
        ),
    )
    return p.parse_args()


def main() -> int:
    """Run the module CLI and return exit code."""
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ns = (args.namespace or args.tenant).strip()
    warnings: list[str] = []

    if args.index_only and args.hydrate_top_n:
        LOGGER.error("--index-only cannot be combined with --hydrate-top-n")
        return 2
    if args.index_only and (args.hydrate_pv_uuids or "").strip():
        LOGGER.error("--index-only cannot be combined with --hydrate-pv-uuids")
        return 2
    if args.hydrate_top_n and not args.pv_index:
        LOGGER.error("--hydrate-top-n requires Pass 1 index (omit --no-pv-index)")
        return 2

    client = endorlabs.Client(tenant=args.tenant)
    try:
        api = getattr(client, "_client", None)
        if api is None:
            raise RuntimeError("Client is closed; API client unavailable.")

        proj = resolve_project(client, ns, args.project, warnings)
        project_name = proj.meta.name if proj.meta and proj.meta.name else proj.uuid
        project_ns = (
            proj.tenant_meta.namespace
            if proj.tenant_meta and proj.tenant_meta.namespace
            else ns
        )
        if (
            ns
            and project_ns != ns
            and not any("resolved the same UUID" in w for w in warnings)
        ):
            warnings.append(
                f"CLI namespace {ns!r} differs from project namespace {project_ns!r}."
            )

        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%SZ")
        slug = slugify(project_name)
        bundle = Path(args.output_dir) / f"{slug}_{ts}"
        bundle.mkdir(parents=True, exist_ok=True)

        run_index = bool(args.pv_index) or bool(args.hydrate_top_n)
        index_rows: list[dict[str, Any]] = []
        inv_meta: dict[str, Any] | None = None
        inventory_block: dict[str, Any] | None = None

        if run_index:
            _pvs, inv_meta = list_package_versions_for_index(
                client,
                namespace=project_ns,
                project_uuid=proj.uuid,
                max_pages=args.pv_index_max_pages,
                page_size=args.pv_index_page_size,
                deterministic=args.deterministic,
            )
            index_rows = build_index_rows(
                _pvs, project_uuid=proj.uuid, namespace=project_ns
            )
            idx_path = bundle / "package_versions_index.json"
            write_json(str(idx_path), index_rows, base_dir=bundle)
            if inv_meta.get("truncated"):
                warnings.append(
                    "Pass 1 package version index may be truncated at list capacity; "
                    "raise --pv-index-max-pages / --pv-index-page-size or narrow scope."
                )
            inventory_block = {
                "enabled": True,
                "artifact_relpath": "package_versions_index.json",
                **inv_meta,
            }
        else:
            inventory_block = {
                "enabled": False,
                "pass": "package_version_index",
                "reason": "disabled_via_no_pv_index",
            }

        hydrate_uuids: list[str] | None = None
        selection_block: dict[str, Any] = {
            "mode": "default_first_pv_limit",
            "hydrate_pv_uuids": None,
            "hydrate_top_n": None,
        }
        raw_hydrate = (args.hydrate_pv_uuids or "").strip()
        if raw_hydrate:
            hydrate_uuids = parse_uuid_list_csv(raw_hydrate)
            selection_block = {
                "mode": "explicit_uuid_list",
                "hydrate_pv_uuids": list(hydrate_uuids),
                "hydrate_top_n": None,
            }
        elif args.hydrate_top_n > 0:
            if not index_rows:
                LOGGER.error("Internal: index_rows empty for hydrate_top_n")
                return 2
            hydrate_uuids = select_top_n_uuids_by_update_time(
                index_rows, args.hydrate_top_n
            )
            selection_block = {
                "mode": "top_n_by_meta_update_time",
                "hydrate_pv_uuids": None,
                "hydrate_top_n": args.hydrate_top_n,
            }

        if args.index_only:
            result = ProjectResult(
                project_uuid=proj.uuid,
                project_name=project_name,
                namespace=project_ns,
                slug=slug,
                out_dir=str(bundle),
                report=(
                    "# Index-only bundle\n\n"
                    "Pass 2 (BOM / call graph / dep_metadata hydration) was skipped. "
                    "Re-run without `--index-only` to hydrate, or use "
                    "`--hydrate-pv-uuids` / `--hydrate-top-n`.\n"
                ),
            )
            _write_text(
                bundle,
                bundle / "dependency-callgraph-summary.md",
                result.report,
            )
        else:
            result = process_project(
                client,
                api,
                args.tenant,
                proj,
                str(bundle),
                pv_limit=args.pv_limit,
                dep_metadata_max_pages=args.dep_metadata_max_pages,
                deterministic=args.deterministic,
                pv_uuid_order=hydrate_uuids if hydrate_uuids else None,
                pv_list_max_pages=args.pv_list_max_pages,
                pv_list_page_size=args.pv_list_page_size,
            )
            _write_text(
                bundle, bundle / "dependency-callgraph-summary.md", result.report
            )
            if result.hydration_missing_pv_uuids:
                missing = result.hydration_missing_pv_uuids[:5]
                warnings.append(
                    "Some requested package version UUIDs were not found in list "
                    f"results (showing up to 5): {missing!r}"
                )
            if result.pv_list_truncated:
                warnings.append(
                    "Pass 2 package version list may be truncated at capacity; "
                    "raise --pv-list-max-pages / --pv-list-page-size."
                )
            if result.dep_metadata_truncated:
                warnings.append(
                    "DependencyMetadata list may be truncated; use "
                    "--dep-metadata-max-pages 0 for unlimited."
                )

        manifest_path = bundle / "context_manifest.json"

        sweep_info: dict[str, Any] | None = None
        if args.callgraph_sweep:
            sweep_dir = bundle / "callgraph_sweep"
            sweep_dir.mkdir(parents=True, exist_ok=True)
            sweep_result = run_callgraph_sweep(
                api,
                project_uuid=proj.uuid,
                out_dir=sweep_dir,
                list_namespace=project_ns,
                max_pages=args.callgraph_max_pages,
                page_size=args.callgraph_page_size,
                decode_zstd=bool(args.decode_zstd),
                client=client,
            )
            if sweep_result.get("call_graph_exports_total") == 0:
                warnings.append(
                    "callgraph_sweep (Pass 3) completed with zero call graph exports "
                    "(no CallGraphData for listed package versions)."
                )
            cap_cg = args.callgraph_max_pages * args.callgraph_page_size
            if sweep_result.get("package_versions_total", 0) >= cap_cg:
                pv_total = sweep_result.get("package_versions_total")
                warnings.append(
                    f"Pass 3 listed {pv_total} package versions (capacity {cap_cg}); "
                    "raise --callgraph-max-pages / --callgraph-page-size if more exist."
                )
            sweep_info = {
                "pass": "callgraph_sweep_pass_3",
                "subdir": "callgraph_sweep",
                "callgraph_sweep_manifest": sweep_result.get("manifest_path", ""),
                "package_versions_total": sweep_result.get("package_versions_total", 0),
                "call_graph_exports_total": sweep_result.get(
                    "call_graph_exports_total", 0
                ),
                "list_max_pages": args.callgraph_max_pages,
                "list_page_size": args.callgraph_page_size,
            }

        hydration_block: dict[str, Any] = {
            "pass_2_dependency_explorer": {
                "skipped": bool(args.index_only),
                "pv_limit": args.pv_limit,
                "used_pv_uuid_order": bool(hydrate_uuids),
                "package_versions_hydrated": len(result.pv_results),
                "missing_pv_uuids": list(result.hydration_missing_pv_uuids),
                "pv_list_truncated": result.pv_list_truncated,
            }
        }

        cli_flags = {
            "tenant": args.tenant,
            "namespace": ns or None,
            "project": args.project,
            "output_dir": args.output_dir,
            "pv_limit": args.pv_limit,
            "dep_metadata_max_pages": args.dep_metadata_max_pages,
            "deterministic": args.deterministic,
            "pv_index": args.pv_index,
            "pv_index_max_pages": args.pv_index_max_pages,
            "pv_index_page_size": args.pv_index_page_size,
            "index_only": args.index_only,
            "hydrate_pv_uuids": args.hydrate_pv_uuids or None,
            "hydrate_top_n": args.hydrate_top_n or None,
            "pv_list_max_pages": args.pv_list_max_pages,
            "pv_list_page_size": args.pv_list_page_size,
            "callgraph_sweep": args.callgraph_sweep,
            "callgraph_max_pages": args.callgraph_max_pages,
            "callgraph_page_size": args.callgraph_page_size,
            "decode_zstd": args.decode_zstd,
        }

        mdata = build_context_manifest(
            version=MANIFEST_VERSION,
            tenant=args.tenant,
            project_uuid=proj.uuid,
            project_name=project_name,
            project_namespace=project_ns,
            cli=cli_flags,
            warnings=warnings,
            project_result=result,
            out_dir=bundle,
            callgraph_sweep=sweep_info,
            inventory=inventory_block,
            selection=selection_block,
            hydration=hydration_block,
        )
        write_json(str(manifest_path), mdata, base_dir=bundle)
        print(str(manifest_path.resolve()))
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
