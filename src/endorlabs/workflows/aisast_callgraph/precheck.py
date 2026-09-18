"""Prechecks: main-context AI-SAST RV, function_summary index, CG PackageVersion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from endorlabs.core.exceptions import NotFoundError
from endorlabs.filters.main_context import main_context_filter, pv_main_context_filter
from endorlabs.workflows.callgraph.resolve import (
    build_callgraph_pv_inventory,
    list_package_versions_for_project,
    order_pvs_for_callgraph,
    pv_inventory_row,
)
from endorlabs.workflows.vector_search.query import (
    list_tenant_vector_stores,
    probe_store_indexed_for_project,
)

GATE_RV = "precheck.repository_version_main_aisast"
GATE_VECTOR = "precheck.function_summary_index"
GATE_CG = "precheck.call_graph_main_pv"


def _empty_evidence() -> dict[str, Any]:
    return {}


def _spec_dict(obj: Any) -> dict[str, Any]:
    spec = getattr(obj, "spec", None)
    if spec is None:
        return {}
    if isinstance(spec, dict):
        return cast("dict[str, Any]", dict(spec))
    if hasattr(spec, "model_dump"):
        return cast("dict[str, Any]", dict(spec.model_dump(exclude_none=False)))
    if hasattr(spec, "__dict__"):
        return cast("dict[str, Any]", dict(vars(spec)))
    return {}


def _aisast_status_str(version: Any) -> str:
    spec = _spec_dict(version)
    st = spec.get("aisast_status")
    return str(st) if st is not None else ""


def _project_repo_name(project: Any) -> str:
    meta = getattr(project, "meta", None)
    if meta is not None and getattr(meta, "name", None):
        return str(meta.name)
    return ""


@dataclass
class GateResult:
    """One named precheck gate."""

    id: str
    ok: bool
    message: str
    evidence: dict[str, Any] = field(default_factory=_empty_evidence)


@dataclass
class PrecheckResult:
    """Aggregate precheck for AI-SAST + Call Graph bridge."""

    ok: bool
    gates: list[GateResult]
    vector_store: Any | None = None
    package_version: Any | None = None
    decoded: Any | None = None
    repo_name: str = ""
    tenant_root: str = ""
    namespace: str = ""

    def as_dict(self) -> dict[str, Any]:
        """JSON-serializable precheck block."""
        return {
            "ok": self.ok,
            "repo_name": self.repo_name,
            "tenant_root": self.tenant_root,
            "namespace": self.namespace,
            "gates": [
                {
                    "id": g.id,
                    "ok": g.ok,
                    "message": g.message,
                    "evidence": g.evidence,
                }
                for g in self.gates
            ],
            "pv_uuid": getattr(self.package_version, "uuid", None),
            "pv_name": (
                getattr(getattr(self.package_version, "meta", None), "name", None)
                if self.package_version is not None
                else None
            ),
            "vector_store_uuid": getattr(self.vector_store, "uuid", None),
        }

    def failed_gate_ids(self) -> list[str]:
        """Return ids of failed gates in order."""
        return [g.id for g in self.gates if not g.ok]


def _gate_main_aisast_rv(
    client: Any,
    project: Any,
    *,
    namespace: str,
    max_pages: int,
) -> GateResult:
    versions = client.RepositoryVersion.list(
        parent=project,
        namespace=namespace,
        filter=main_context_filter(),
        max_pages=max_pages,
    )
    statuses = [_aisast_status_str(v) for v in versions]
    success_rows = [s for s in statuses if "SUCCESS" in s.upper()]
    if not versions:
        return GateResult(
            id=GATE_RV,
            ok=False,
            message=(
                "No CONTEXT_TYPE_MAIN RepositoryVersion rows for this project; "
                "bridge only supports main-context repository versions."
            ),
            evidence={"version_count": 0, "aisast_statuses": []},
        )
    if not success_rows:
        return GateResult(
            id=GATE_RV,
            ok=False,
            message=(
                "MAIN RepositoryVersion(s) present but none report "
                "aisast_status SUCCESS."
            ),
            evidence={
                "version_count": len(versions),
                "aisast_statuses": statuses[:20],
            },
        )
    return GateResult(
        id=GATE_RV,
        ok=True,
        message="MAIN RepositoryVersion with AI-SAST SUCCESS found.",
        evidence={
            "version_count": len(versions),
            "success_count": len(success_rows),
            "aisast_statuses": statuses[:20],
        },
    )


def _gate_function_summary(
    client: Any,
    *,
    tenant_root: str,
    repo_name: str,
) -> tuple[GateResult, Any | None, str]:
    stores = [
        s
        for s in list_tenant_vector_stores(
            client,
            namespace=tenant_root,
            name_substring="function_summary",
            max_pages=1,
        )
        if getattr(getattr(s, "meta", None), "name", None) == "function_summary"
    ]
    candidates = [r for r in (repo_name, repo_name.lower()) if r]
    probe_evidence: dict[str, Any] = {
        "store_count": len(stores),
        "repo_candidates": candidates,
    }
    if not stores:
        return (
            GateResult(
                id=GATE_VECTOR,
                ok=False,
                message=(
                    f"No VectorStore named function_summary in tenant root "
                    f"{tenant_root!r}."
                ),
                evidence=probe_evidence,
            ),
            None,
            repo_name,
        )
    if not candidates:
        return (
            GateResult(
                id=GATE_VECTOR,
                ok=False,
                message=(
                    "Project has no meta.name; cannot probe vector index by repo."
                ),
                evidence=probe_evidence,
            ),
            stores[0],
            repo_name,
        )

    vector_store = stores[0]
    for cand in candidates:
        probe = probe_store_indexed_for_project(client, vector_store, cand)
        probe_evidence["last_probe"] = probe
        if probe.get("indexed"):
            return (
                GateResult(
                    id=GATE_VECTOR,
                    ok=True,
                    message=f"function_summary indexed for repo={cand!r}.",
                    evidence={**probe_evidence, "repo": cand},
                ),
                vector_store,
                cand,
            )
    return (
        GateResult(
            id=GATE_VECTOR,
            ok=False,
            message=(
                f"function_summary store exists but is not indexed for "
                f"repo={candidates[0]!r}."
            ),
            evidence=probe_evidence,
        ),
        vector_store,
        repo_name,
    )


def _gate_main_callgraph(
    client: Any,
    project: Any,
    *,
    namespace: str,
    max_pages: int,
    page_size: int,
    max_decode_attempts: int | None,
) -> tuple[GateResult, Any | None, Any | None]:
    pvs = list_package_versions_for_project(
        client,
        project,
        namespace=namespace,
        max_pages=max_pages,
        page_size=page_size,
        filter=pv_main_context_filter(),
    )
    inventory = build_callgraph_pv_inventory(project, pvs, namespace=namespace)
    candidates_pv = order_pvs_for_callgraph(pvs)
    cg_evidence: dict[str, Any] = {
        "package_versions_listed": inventory.get("package_versions_listed"),
        "call_graph_available_count": inventory.get("call_graph_available_count"),
        "inventory_message": inventory.get("message"),
        "sample_pvs": [pv_inventory_row(pv) for pv in candidates_pv[:5]],
    }
    if not candidates_pv:
        return (
            GateResult(
                id=GATE_CG,
                ok=False,
                message=(
                    "No CONTEXT_TYPE_MAIN PackageVersion with "
                    "call_graph_available=true for this project."
                ),
                evidence=cg_evidence,
            ),
            None,
            None,
        )

    limit = (
        len(candidates_pv)
        if max_decode_attempts is None
        else min(max_decode_attempts, len(candidates_pv))
    )
    decode_failures: list[str] = []
    for pv in candidates_pv[:limit]:
        try:
            decoded_try = client.CallGraphData.decode(pv)
        except NotFoundError:
            decode_failures.append(str(getattr(pv, "uuid", "")))
            continue
        if decoded_try is not None and decoded_try.callables is not None:
            return (
                GateResult(
                    id=GATE_CG,
                    ok=True,
                    message=("MAIN PackageVersion with decodable CallGraphData found."),
                    evidence={
                        **cg_evidence,
                        "pv_uuid": pv.uuid,
                        "n_callables": len(decoded_try.callables or []),
                        "n_edges": len(decoded_try.edges or []),
                    },
                ),
                pv,
                decoded_try,
            )
        decode_failures.append(str(getattr(pv, "uuid", "")))

    cg_evidence["decode_failures"] = decode_failures
    return (
        GateResult(
            id=GATE_CG,
            ok=False,
            message=(
                "MAIN call_graph_available PackageVersion(s) found but "
                "CallGraphData.decode failed for all tried."
            ),
            evidence=cg_evidence,
        ),
        None,
        None,
    )


def precheck_aisast_and_callgraph(
    client: Any,
    project: Any,
    *,
    tenant_root: str,
    namespace: str,
    max_pages: int = 50,
    page_size: int = 200,
    max_decode_attempts: int | None = None,
) -> PrecheckResult:
    """Hard-gate MAIN AI-SAST RVs, function_summary index, and MAIN CG PV."""
    repo_name = _project_repo_name(project)
    gates: list[GateResult] = [
        _gate_main_aisast_rv(client, project, namespace=namespace, max_pages=max_pages)
    ]
    vec_gate, vector_store, repo_name = _gate_function_summary(
        client, tenant_root=tenant_root, repo_name=repo_name
    )
    gates.append(vec_gate)
    cg_gate, package_version, decoded = _gate_main_callgraph(
        client,
        project,
        namespace=namespace,
        max_pages=max_pages,
        page_size=page_size,
        max_decode_attempts=max_decode_attempts,
    )
    gates.append(cg_gate)
    ok = all(g.ok for g in gates)
    return PrecheckResult(
        ok=ok,
        gates=gates,
        vector_store=vector_store,
        package_version=package_version if ok else None,
        decoded=decoded if ok else None,
        repo_name=repo_name,
        tenant_root=tenant_root,
        namespace=namespace,
    )
