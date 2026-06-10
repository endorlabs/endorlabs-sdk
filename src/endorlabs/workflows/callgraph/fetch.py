"""Call graph API fetch and summary artifact helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from endorlabs.utils.api_pagination import extract_objects
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.callgraph.proto_decode import _HAS_ZSTD, decode_callgraph
from endorlabs.workflows.callgraph.render import render_callgraph_analysis

if TYPE_CHECKING:
    from endorlabs import Client
    from endorlabs.api_client import APIClient

logger = get_resource_logger(__name__)


def retrieve_call_graph_full(
    api_client: APIClient,
    namespace: str,
    pv_uuid: str,
) -> dict[str, Any]:
    """Retrieve the full call graph data for a PackageVersion.

    Uses ``x-callgraph-encoding=any`` header to request JSON encoding.
    """
    from endorlabs.operations import validate_namespace

    ns = validate_namespace(namespace)
    url = f"v1/namespaces/{ns}/call-graph-data"
    params = {
        "list_parameters.filter": f'meta.parent_uuid=="{pv_uuid}"',
        "list_parameters.page_size": "1",
    }
    resp = api_client.get(url, params=params)
    data = resp.json()
    objects = extract_objects(data)
    if not objects:
        return {}

    cg_uuid = objects[0].get("uuid", "")
    if not cg_uuid:
        return objects[0]

    get_url = f"v1/namespaces/{ns}/call-graph-data/{cg_uuid}"
    try:
        resp_full = api_client.get(
            get_url,
            headers={"x-callgraph-encoding": "any"},
        )
        return resp_full.json()
    except Exception as exc:
        logger.warning("  Unable to GET full call graph %s: %s", cg_uuid, exc)
        return objects[0]


def retrieve_call_graph_for_client(
    client: Client,
    namespace: str,
    pv_uuid: str,
) -> dict[str, Any]:
    """Retrieve call graph data using a high-level ``Client`` instance."""
    api_client = getattr(client, "_client", None)
    if api_client is None:
        raise RuntimeError("Client is closed; cannot retrieve call graph data.")
    return retrieve_call_graph_full(api_client, namespace, pv_uuid)


def summarize_call_graph(cg_data: dict[str, Any]) -> dict[str, Any]:
    """Extract a human-readable summary dict from raw call graph data."""
    summary: dict[str, Any] = {
        "uuid": cg_data.get("uuid", ""),
        "top_level_keys": list(cg_data.keys()),
    }
    meta = cg_data.get("meta", {})
    if meta:
        summary["name"] = meta.get("name", "")
        summary["parent_uuid"] = meta.get("parent_uuid", "")
    spec = cg_data.get("spec", {})
    if spec:
        summary["spec_keys"] = list(spec.keys())
        any_data = spec.get("any", {})
        if any_data and isinstance(any_data, dict):
            summary["call_graph_format"] = "json (any)"
            summary["call_graph_top_keys"] = list(any_data.keys())[:20]
        elif spec.get("zstd_bytes"):
            summary["call_graph_format"] = "zstd_bytes (binary)"
            zb = spec["zstd_bytes"]
            summary["zstd_bytes_length"] = (
                len(zb) if isinstance(zb, (str, bytes)) else "?"
            )
        elif spec.get("storage_url"):
            summary["call_graph_format"] = "external_storage"
        elif spec.get("related_object"):
            summary["call_graph_format"] = "related_object reference"
    return summary


_ENDORCTL_WORKSPACE_MARKER = "endorctl/"


def _clean_source_path(path: str) -> str:
    """Strip ``<scan-root>/endorctl/<project>/`` from call-graph source paths."""
    if _ENDORCTL_WORKSPACE_MARKER not in path:
        return path
    after_project_slug = path.split(_ENDORCTL_WORKSPACE_MARKER, 1)[1]
    if "/" in after_project_slug:
        return after_project_slug.split("/", 1)[1]
    return after_project_slug


def render_call_graph_summary_md(cg_json_path: str | Path) -> str | None:
    """Decode a call graph JSON and return a compact Markdown summary.

    Returns ``None`` if ``zstandard`` is unavailable or data lacks ``zstd_bytes``.
    """
    if not _HAS_ZSTD:
        return None
    try:
        with open(cg_json_path, encoding="utf-8") as f:
            envelope = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Unable to read call graph JSON %s: %s", cg_json_path, exc)
        return None
    if "zstd_bytes" not in envelope:
        return None
    try:
        info = decode_callgraph(envelope)
    except Exception as exc:
        logger.warning("Unable to decode call graph: %s", exc)
        return None

    total_fp = sum(len(t.methods) for t in info.internal_types)
    total_tp = sum(len(t.methods) for t in info.external_types)
    lines: list[str] = [
        f"{info.language} | {total_fp} first-party functions | "
        f"{total_tp} third-party stubs | {len(info.call_edges)} call edges",
        "",
    ]
    file_funcs: dict[str, list[str]] = {}
    for t in info.internal_types:
        src = _clean_source_path(t.source_file) if t.source_file else "(unknown)"
        if src not in file_funcs:
            file_funcs[src] = []
        for m in t.methods:
            fn = m.uri
            if "]/" in fn:
                fn = fn.rsplit("]/", 1)[-1]
            if not fn or fn == "()":
                continue
            fn = fn.split(".anonymous_function")[0]
            if fn and fn not in file_funcs[src]:
                file_funcs[src].append(fn)

    lines.append("| Source File | Key Functions |")
    lines.append("|-------------|---------------|")
    for src in sorted(file_funcs.keys()):
        funcs = file_funcs[src] or ["(module init)"]
        func_str = ", ".join(f"`{f}`" for f in funcs[:4])
        if len(funcs) > 4:
            func_str += f" (+{len(funcs) - 4} more)"
        lines.append(f"| `{src}` | {func_str} |")
    return "\n".join(lines)


def generate_call_graph_analysis_md(cg_json_path: str | Path) -> str | None:
    """Decode a call graph JSON and write an ``_analysis.md`` alongside it.

    Returns the path to the generated file, or ``None`` on failure.
    """
    if not _HAS_ZSTD:
        return None
    cg_json_path = Path(cg_json_path)
    try:
        envelope = json.loads(cg_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Unable to read call graph JSON %s: %s", cg_json_path, exc)
        return None
    if "zstd_bytes" not in envelope:
        return None
    try:
        info = decode_callgraph(envelope)
        md = render_callgraph_analysis(info)
    except Exception as exc:
        logger.warning("Unable to generate call graph analysis: %s", exc)
        return None

    out_path = cg_json_path.with_name(cg_json_path.stem + "_analysis.md")
    safe_write_text(cg_json_path.parent, out_path, md)
    logger.info("  Wrote %s", out_path)
    return str(out_path)
