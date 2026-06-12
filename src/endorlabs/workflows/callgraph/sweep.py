"""Enumerate package versions and export call graph artifacts (decode optional)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from endorlabs.core.exceptions import NotFoundError
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.path_safety import safe_write_text

LOGGER = get_resource_logger(__name__)


def _write_json_base(root: Path, path: Path, data: Any) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    safe_write_text(root, path, text)


def run_callgraph_sweep(
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
    namespace). ``client`` is ``endorlabs.Client`` for
    ``PackageVersion.list_by_project``.
    """
    from types import SimpleNamespace

    source = SimpleNamespace(
        uuid=project_uuid,
        tenant_meta=SimpleNamespace(namespace=list_namespace),
    )
    route = client.PackageVersion.list_by_project(
        source,
        namespace=list_namespace,
        max_pages=max_pages,
        page_size=page_size,
    )
    pvs = route.values or []

    exports: list[dict[str, Any]] = []
    for idx, pv in enumerate(pvs, start=1):
        decoded = None
        try:
            if decode_zstd:
                decoded = client.CallGraphData.decode(pv)
                cg_data = decoded.envelope
            else:
                cg_data = client.CallGraphData.fetch(pv)
        except NotFoundError:
            continue
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

        if decode_zstd and decoded is not None:
            summary_file = out_dir / f"{idx:04d}_{pv.uuid}.decoded_summary.json"
            callables_file = out_dir / f"{idx:04d}_{pv.uuid}.decoded_callables.json"
            edges_file = out_dir / f"{idx:04d}_{pv.uuid}.decoded_edges.json"
            _write_json_base(out_dir, summary_file, decoded.summary)
            _write_json_base(out_dir, callables_file, decoded.callables)
            _write_json_base(out_dir, edges_file, decoded.edges)
            row["decoded_summary_file"] = str(summary_file)
            row["decoded_callables_file"] = str(callables_file)
            row["decoded_edges_file"] = str(edges_file)

        exports.append(row)

    return {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "project_uuid": project_uuid,
        "list_namespace": list_namespace,
        "package_versions_total": len(pvs),
        "call_graph_exports_total": len(exports),
        "exports": exports,
    }
