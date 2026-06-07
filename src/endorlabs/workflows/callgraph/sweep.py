"""Enumerate package versions and export call graph artifacts (decode optional)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from endorlabs import F
from endorlabs.tools.dependency_explorer import retrieve_call_graph_full
from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.callgraph.decoded import decode_payload

LOGGER = logging.getLogger(__name__)


def _write_json_base(root: Path, path: Path, data: Any) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    safe_write_text(root, path, text)


def run_callgraph_sweep(
    api_client: Any,
    *,
    project_uuid: str,
    out_dir: Path,
    list_namespace: str,
    max_pages: int,
    page_size: int,
    decode_zstd: bool,
    client: Any,
) -> dict[str, Any]:
    """List package versions for the project and write call graph exports.

    `list_namespace` is where PackageVersion is listed (same as project tenant
    namespace). ``client`` is ``endorlabs.Client`` for ``PackageVersion.list``.
    """
    pvs = client.PackageVersion.list(
        namespace=list_namespace,
        filter=F("spec.project_uuid") == project_uuid,
        max_pages=max_pages,
        page_size=page_size,
    )

    exports: list[dict[str, Any]] = []
    for idx, pv in enumerate(pvs, start=1):
        cg_data = retrieve_call_graph_full(api_client, list_namespace, pv.uuid)
        if not cg_data:
            continue

        raw_file = out_dir / f"{idx:04d}_{pv.uuid}.call_graph.json"
        _write_json_base(out_dir, raw_file, cg_data)

        row: dict[str, Any] = {
            "pv_uuid": pv.uuid,
            "pv_name": pv.meta.name if pv.meta and pv.meta.name else pv.uuid,
            "raw_file": str(raw_file),
            "call_graph_uuid": cg_data.get("uuid"),
            "parent_uuid": (cg_data.get("meta") or {}).get("parent_uuid"),
        }

        if decode_zstd and "zstd_bytes" in cg_data:
            summary, callables, edges = decode_payload(cg_data)
            summary_file = out_dir / f"{idx:04d}_{pv.uuid}.decoded_summary.json"
            callables_file = out_dir / f"{idx:04d}_{pv.uuid}.decoded_callables.json"
            edges_file = out_dir / f"{idx:04d}_{pv.uuid}.decoded_edges.json"
            _write_json_base(out_dir, summary_file, summary)
            _write_json_base(out_dir, callables_file, callables)
            _write_json_base(out_dir, edges_file, edges)
            row["decoded_summary_file"] = str(summary_file)
            row["decoded_callables_file"] = str(callables_file)
            row["decoded_edges_file"] = str(edges_file)

        exports.append(row)

    manifest: dict[str, Any] = {
        "package_versions_total": len(pvs),
        "call_graph_exports_total": len(exports),
        "exports": exports,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    manifest_path = out_dir / "callgraph_sweep_manifest.json"
    _write_json_base(out_dir, manifest_path, manifest)
    LOGGER.info("Wrote %s", manifest_path)
    return {
        "manifest_path": str(manifest_path),
        "package_versions_total": len(pvs),
        "call_graph_exports_total": len(exports),
    }
