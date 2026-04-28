#!/usr/bin/env python3
"""Fetch call graph artifacts for an Endor Labs project.

This script is intentionally sanitized: no hardcoded tenant names, UUIDs, or
customer-specific values.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs import F
from endorlabs.tools.dependency_explorer import (
    decode_callgraph,
    retrieve_call_graph_full,
)

LOGGER = logging.getLogger(__name__)


def _slug(value: str) -> str:
    out = []
    for ch in value:
        if ch.isalnum() or ch in ("-", "_", "."):
            out.append(ch)
        else:
            out.append("_")
    return "".join(out).strip("_") or "project"


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _find_project(client: endorlabs.Client, namespace: str, project: str) -> Any:
    if len(project) == 24 and all(c in "0123456789abcdef" for c in project.lower()):
        return client.Project.get(project, namespace=namespace)
    return client.Project.lookup(name=project, namespace=namespace, traverse=True)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for call graph fetch."""
    parser = argparse.ArgumentParser(
        description="Fetch and decode project call graph data."
    )
    parser.add_argument(
        "--tenant",
        required=True,
        help="Tenant/namespace for client auth context.",
    )
    parser.add_argument(
        "--namespace",
        required=True,
        help="Namespace where the project lives (often same as tenant).",
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Project UUID (24-hex) or exact project name (e.g., repository URL).",
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp/callgraph_exports",
        help="Base output directory. Default: .tmp/callgraph_exports",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Max pages for PackageVersion listing. Default: 50",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=200,
        help="Page size for PackageVersion listing. Default: 200",
    )
    parser.add_argument(
        "--decode-zstd",
        action="store_true",
        help="Decode zstd_bytes and emit decoded summary/callables/edges files.",
    )
    return parser.parse_args()


def main() -> int:
    """Fetch project call graphs and write artifacts to disk."""
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    client = endorlabs.Client(tenant=args.tenant)
    api_client = getattr(client, "_client", None)
    if api_client is None:
        raise RuntimeError("Client is closed; API client unavailable.")

    project = _find_project(client, args.namespace, args.project)
    project_name = (
        project.meta.name if project.meta and project.meta.name else project.uuid
    )
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%SZ")
    out_dir = Path(args.output_dir) / f"{_slug(project_name)}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    pvs = client.PackageVersion.list(
        namespace=args.namespace,
        filter=F("spec.project_uuid") == project.uuid,
        max_pages=args.max_pages,
        page_size=args.page_size,
    )

    exports: list[dict[str, Any]] = []
    for idx, pv in enumerate(pvs, start=1):
        cg_data = retrieve_call_graph_full(api_client, args.namespace, pv.uuid)
        if not cg_data:
            continue

        raw_file = out_dir / f"{idx:04d}_{pv.uuid}.call_graph.json"
        _write_json(raw_file, cg_data)

        row: dict[str, Any] = {
            "pv_uuid": pv.uuid,
            "pv_name": pv.meta.name if pv.meta and pv.meta.name else pv.uuid,
            "raw_file": str(raw_file),
            "call_graph_uuid": cg_data.get("uuid"),
            "parent_uuid": (cg_data.get("meta") or {}).get("parent_uuid"),
        }

        if args.decode_zstd and "zstd_bytes" in cg_data:
            decoded = decode_callgraph(cg_data)
            all_callables = [
                method
                for typ in (decoded.internal_types + decoded.external_types)
                for method in typ.methods
            ]
            summary_file = out_dir / f"{idx:04d}_{pv.uuid}.decoded_summary.json"
            callables_file = out_dir / f"{idx:04d}_{pv.uuid}.decoded_callables.json"
            edges_file = out_dir / f"{idx:04d}_{pv.uuid}.decoded_edges.json"

            _write_json(
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
            _write_json(
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
                    for method in sorted(all_callables, key=lambda item: item.method_id)
                ],
            )
            _write_json(
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

    manifest = {
        "tenant": args.tenant,
        "namespace": args.namespace,
        "project_uuid": project.uuid,
        "project_name": project_name,
        "package_versions_total": len(pvs),
        "call_graph_exports_total": len(exports),
        "exports": exports,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    manifest_path = out_dir / "manifest.json"
    _write_json(manifest_path, manifest)
    LOGGER.info("Wrote manifest: %s", manifest_path)
    LOGGER.info("Output directory: %s", out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
