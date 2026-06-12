"""Pass-1 wide index: list PackageVersions for a project and emit compact index rows."""

from __future__ import annotations

from typing import Any

from endorlabs.utils.logging_config import get_resource_logger

LOGGER = get_resource_logger(__name__)


def _iso_timestamp(val: Any) -> str | None:
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        try:
            out = val.isoformat()
            return str(out)
        except (TypeError, ValueError):
            return None
    return str(val)


def source_ref_sha_from_pv(pv: Any) -> tuple[str | None, str | None]:
    """Extract ref and sha from PackageVersion.spec.source_code_reference."""
    spec = getattr(pv, "spec", None)
    if not spec:
        return None, None
    scr = getattr(spec, "source_code_reference", None)
    if not scr:
        return None, None
    ref = getattr(scr, "ref", None)
    sha = getattr(scr, "sha", None)
    ver = getattr(scr, "version", None)
    if ver is not None:
        if ref is None:
            ref = getattr(ver, "ref", None)
        if sha is None:
            sha = getattr(ver, "sha", None)
    return (
        str(ref) if ref is not None else None,
        str(sha) if sha is not None else None,
    )


def index_row_from_pv(pv: Any, *, project_uuid: str, namespace: str) -> dict[str, Any]:
    """One compact row for ``package_versions_index.json``."""
    meta = getattr(pv, "meta", None)
    name = getattr(meta, "name", None) if meta else None
    if not name:
        name = getattr(pv, "uuid", "") or ""
    spec = getattr(pv, "spec", None)
    eco = getattr(spec, "ecosystem", None) if spec else None
    lang = getattr(spec, "language", None) if spec else None
    pkg = getattr(spec, "package_name", None) if spec else None
    rel = getattr(spec, "relative_path", None) if spec else None
    cg_ok = getattr(spec, "call_graph_available", None) if spec else None
    pcg = getattr(spec, "precomputed_call_graph_state", None) if spec else None
    if pcg is not None and hasattr(pcg, "model_dump"):
        pcg = pcg.model_dump(mode="json", warnings=False)
    elif pcg is not None and not isinstance(pcg, (str, dict, type(None))):
        pcg = str(pcg)
    ref, sha = source_ref_sha_from_pv(pv)
    create_t = _iso_timestamp(getattr(meta, "create_time", None)) if meta else None
    update_t = _iso_timestamp(getattr(meta, "update_time", None)) if meta else None
    upsert_t = _iso_timestamp(getattr(meta, "upsert_time", None)) if meta else None
    return {
        "pv_uuid": getattr(pv, "uuid", None) or "",
        "pv_name": str(name),
        "namespace": namespace,
        "project_uuid": project_uuid,
        "ecosystem": str(eco) if eco is not None else None,
        "language": str(lang) if lang is not None else None,
        "package_name": str(pkg) if pkg is not None else None,
        "relative_path": str(rel) if rel is not None else None,
        "source_ref": ref,
        "source_sha": sha,
        "call_graph_available": cg_ok,
        "precomputed_call_graph_state": pcg,
        "meta_create_time": create_t,
        "meta_update_time": update_t,
        "meta_upsert_time": upsert_t,
    }


def list_package_versions_for_index(
    client: Any,
    *,
    namespace: str,
    project_uuid: str,
    max_pages: int,
    page_size: int,
    deterministic: bool,
) -> tuple[list[Any], dict[str, Any]]:
    """Return raw PV list and inventory metadata for manifest ``inventory``."""
    from types import SimpleNamespace

    source = SimpleNamespace(
        uuid=project_uuid,
        tenant_meta=SimpleNamespace(namespace=namespace),
    )
    route = client.PackageVersion.list_by_project(
        source,
        namespace=namespace,
        max_pages=max_pages,
        page_size=page_size,
    )
    pvs = route.values or []
    cap = max_pages * page_size
    truncated = len(pvs) >= cap
    truncation_reason: str | None = None
    if truncated:
        truncation_reason = (
            f"Listed {len(pvs)} package versions (capacity {cap} = "
            f"max_pages={max_pages} * page_size={page_size}); "
            "more may exist — raise caps or narrow scope."
        )
        LOGGER.warning("%s", truncation_reason)
    if deterministic:
        pvs = sorted(
            pvs,
            key=lambda pv: str(
                getattr(getattr(pv, "meta", None), "name", None) or pv.uuid
            ),
        )
    meta: dict[str, Any] = {
        "pass": "package_version_index",
        "max_pages": max_pages,
        "page_size": page_size,
        "capacity_rows": cap,
        "total_package_versions_seen": len(pvs),
        "truncated": truncated,
        "truncation_reason": truncation_reason,
        "coverage_mode": (
            "truncated_at_capacity" if truncated else "full_within_list_cap"
        ),
        "has_scan_status": False,
        "has_dep_counts": False,
        "errors_summary": {"count": 0, "samples": []},
    }
    return pvs, meta


def build_index_rows(
    pvs: list[Any],
    *,
    project_uuid: str,
    namespace: str,
) -> list[dict[str, Any]]:
    """Map package version resources to slim index rows for Pass 1 export."""
    return [
        index_row_from_pv(pv, project_uuid=project_uuid, namespace=namespace)
        for pv in pvs
    ]


def select_top_n_uuids_by_update_time(rows: list[dict[str, Any]], n: int) -> list[str]:
    """Return up to *n* pv_uuid values, newest ``meta_update_time`` first."""

    def sort_key(r: dict[str, Any]) -> str:
        return r.get("meta_update_time") or r.get("meta_upsert_time") or ""

    sorted_rows = sorted(
        rows,
        key=sort_key,
        reverse=True,
    )
    out: list[str] = []
    for r in sorted_rows:
        uid = r.get("pv_uuid")
        if uid and isinstance(uid, str):
            out.append(uid)
        if len(out) >= n:
            break
    return out


def parse_uuid_list_csv(raw: str) -> list[str]:
    """Parse comma-separated UUIDs (24-hex), strip, drop empties."""
    parts = [p.strip() for p in raw.replace(";", ",").split(",")]
    return [p for p in parts if p]
