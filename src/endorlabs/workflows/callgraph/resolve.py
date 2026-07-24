"""Resolve a package version with decodable CallGraphData."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from endorlabs.core.exceptions import NotFoundError
from endorlabs.resources.call_graph_data import CallGraphDecoded
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.agent_context.package_versions import source_ref_sha_from_pv

LOGGER = get_resource_logger(__name__)

_MAIN_REF_RANKS: dict[str, int] = {
    "refs/heads/main": 0,
    "main": 0,
    "refs/heads/master": 1,
    "master": 1,
}


def _source_ref_sha_from_pv(pv: Any) -> tuple[str | None, str | None]:
    return source_ref_sha_from_pv(pv)


def pv_call_graph_available(pv: Any) -> bool:
    """Return True when ``PackageVersion.spec.call_graph_available`` is set."""
    spec = getattr(pv, "spec", None)
    if not spec:
        return False
    if isinstance(spec, dict):
        return bool(spec.get("call_graph_available", False))
    return bool(getattr(spec, "call_graph_available", False))


def _ref_sort_rank(ref: str | None) -> int:
    if not ref:
        return 3
    return _MAIN_REF_RANKS.get(ref.lower().strip(), 2)


def order_pvs_for_callgraph(pvs: list[Any]) -> list[Any]:
    """Return PVs with ``call_graph_available``, main branch refs first."""
    available = [pv for pv in pvs if pv_call_graph_available(pv)]
    if not available:
        return []

    def sort_key(pv: Any) -> tuple[int, str, str]:
        ref, _sha = _source_ref_sha_from_pv(pv)
        meta = getattr(pv, "meta", None)
        update_t = ""
        if meta is not None:
            raw = getattr(meta, "update_time", None)
            if raw is not None and hasattr(raw, "isoformat"):
                update_t = raw.isoformat()
            else:
                update_t = str(raw or "")
        return (_ref_sort_rank(ref), ref or "", update_t)

    return sorted(available, key=sort_key, reverse=False)


def pv_inventory_row(pv: Any) -> dict[str, Any]:
    """One diagnostic row for call-graph PV selection."""
    ref, sha = _source_ref_sha_from_pv(pv)
    meta = getattr(pv, "meta", None)
    name = getattr(meta, "name", None) if meta else None
    return {
        "pv_uuid": getattr(pv, "uuid", None) or "",
        "pv_name": str(name) if name else getattr(pv, "uuid", ""),
        "source_ref": ref,
        "source_sha": sha,
        "call_graph_available": pv_call_graph_available(pv),
    }


def build_callgraph_pv_inventory(
    project: Any,
    pvs: list[Any],
    *,
    namespace: str,
) -> dict[str, Any]:
    """Summarize listed PVs and whether any have call graphs for this project."""
    rows = [pv_inventory_row(pv) for pv in pvs]
    available_rows = [row for row in rows if row["call_graph_available"]]
    project_uuid = getattr(project, "uuid", None) or ""
    project_name = ""
    meta = getattr(project, "meta", None)
    if meta is not None and getattr(meta, "name", None):
        project_name = str(meta.name)

    message = ""
    if not pvs:
        message = (
            f"No PackageVersion rows listed for project {project_uuid!r} "
            f"in namespace {namespace!r}."
        )
    elif not available_rows:
        refs = sorted(
            {row["source_ref"] or "<no-ref>" for row in rows},
        )
        message = (
            f"No PackageVersion with spec.call_graph_available=true for project "
            f"{project_uuid!r} ({project_name or 'unknown'}) in namespace "
            f"{namespace!r}; listed {len(rows)} PV(s) across refs {refs!r}."
        )
    else:
        main_rows = [
            row for row in available_rows if _ref_sort_rank(row.get("source_ref")) <= 1
        ]
        ordered_refs = [row["source_ref"] for row in available_rows]
        message = (
            f"Found {len(available_rows)} PV(s) with call_graph_available=true "
            f"(refs in try order: {ordered_refs!r}"
            + (
                f"; main/master candidates: {len(main_rows)}"
                if main_rows
                else "; no main/master ref among available PVs"
            )
            + ")."
        )

    return {
        "project_uuid": project_uuid,
        "project_name": project_name or None,
        "namespace": namespace,
        "package_versions_listed": len(rows),
        "call_graph_available_count": len(available_rows),
        "package_versions": rows,
        "message": message,
    }


def list_package_versions_for_project(
    client: Any,
    project: Any,
    *,
    namespace: str,
    max_pages: int = 50,
    page_size: int = 200,
) -> list[Any]:
    """List package versions for *project* in *namespace*."""
    return client.PackageVersion.list_by_project(
        project,
        namespace=namespace,
        max_pages=max_pages,
        page_size=page_size,
    )


def resolve_package_version_with_callgraph(
    client: Any,
    project: Any,
    *,
    namespace: str,
    max_pages: int = 50,
    page_size: int = 200,
    max_attempts: int | None = None,
    inventory_out: dict[str, Any] | None = None,
) -> tuple[Any, CallGraphDecoded] | None:
    """Return the first decodable (PV, graph) with ``call_graph_available`` set.

    Candidates are ordered: ``refs/heads/main`` / ``main`` first, then other
    refs, then remaining ``call_graph_available`` rows. Skips PVs that raise
    ``NotFoundError`` on decode. Logs and optionally fills *inventory_out*
    when no suitable PV exists.
    """
    pvs = list_package_versions_for_project(
        client,
        project,
        namespace=namespace,
        max_pages=max_pages,
        page_size=page_size,
    )
    inventory = build_callgraph_pv_inventory(project, pvs, namespace=namespace)
    if inventory_out is not None:
        inventory_out.clear()
        inventory_out.update(inventory)

    candidates = order_pvs_for_callgraph(pvs)
    if not candidates:
        LOGGER.warning("%s", inventory["message"])
        return None

    limit = (
        len(candidates) if max_attempts is None else min(max_attempts, len(candidates))
    )
    decode_failures: list[str] = []

    for pv in candidates[:limit]:
        ref, _sha = _source_ref_sha_from_pv(pv)
        try:
            decoded = client.CallGraphData.decode(pv)
        except NotFoundError:
            decode_failures.append(f"{pv.uuid}@{ref or '?'}")
            continue
        if decoded is not None and decoded.callables is not None:
            return pv, decoded

    fail_msg = (
        f"Found {len(candidates)} PV(s) with call_graph_available=true for project "
        f"{inventory['project_uuid']!r} but CallGraphData.decode failed for all "
        f"{limit} tried: {decode_failures!r}."
    )
    LOGGER.warning("%s", fail_msg)
    if inventory_out is not None:
        inventory_out["message"] = fail_msg
        inventory_out["decode_failures"] = decode_failures
    return None


def project_as_list_source(project_uuid: str, list_namespace: str) -> SimpleNamespace:
    """Minimal project-shaped object for ``list_by_project``."""
    return SimpleNamespace(
        uuid=project_uuid,
        tenant_meta=SimpleNamespace(namespace=list_namespace),
    )
