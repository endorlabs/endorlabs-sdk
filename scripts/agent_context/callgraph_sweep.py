"""Enumerate package versions and export call graph artifacts (decode optional)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from endorlabs import F
from endorlabs.tools.dependency_explorer import (
    decode_callgraph,
    retrieve_call_graph_full,
)
from endorlabs.utils.path_safety import safe_write_text

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
    """List all package versions for the project and write call graph exports + manifest.

    `list_namespace` is where PackageVersion is listed (same as project tenant
    namespace). ``client`` is ``endorlabs.Client`` for ``PackageVersion.list``."""
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
            decoded = decode_callgraph(cg_data)
            all_callables = [
                method
                for typ in (decoded.internal_types + decoded.external_types)
                for method in typ.methods
            ]
            summary_file = out_dir / f"{idx:04d}_{pv.uuid}.decoded_summary.json"
            callables_file = out_dir / f"{idx:04d}_{pv.uuid}.decoded_callables.json"
            edges_file = out_dir / f"{idx:04d}_{pv.uuid}.decoded_edges.json"
            _write_json_base(
                out_dir,
                summary_file,
                {
                    "uuid": decoded.uuid,
                    "namespace": decoded.namespace,
                    "parent_uuid": decoded.parent_uuid,
                    "package_name": decoded.package_name,
                    "language": decoded.language,
                    "version": decoded.version,
                    "internal_types": len(decoded.internal_types),
                    "external_types": len(decoded.external_types),
                    "call_edges": len(decoded.call_edges),
                    "total_callables": len(all_callables),
                },
            )
            _write_json_base(
                out_dir,
                callables_file,
                [
                    {
                        "method_id": method.method_id,
                        "uri": method.uri,
                        "access": method.access,
                        "first_line": method.first_line,
                        "last_line": method.last_line,
                        "defined": method.defined,
                    }
                    for method in sorted(
                        all_callables, key=lambda item: item.method_id
                    )
                ],
            )
            _write_json_base(
                out_dir,
                edges_file,
                [
                    {
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "source_uri": decoded.callable_label(edge.source_id),
                        "target_uri": decoded.callable_label(edge.target_id),
                        "callsite_count": len(edge.callsites),
                        "call_types": sorted({s.call_type for s in edge.callsites}),
                    }
                    for edge in decoded.call_edges
                ],
            )
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
