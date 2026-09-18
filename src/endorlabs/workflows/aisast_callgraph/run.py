"""Orchestrate AI-SAST function_summary → Call Graph bridge."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from endorlabs.workflows.aisast_callgraph.join import (
    WALK_DISCLAIMER,
    match_seeds_to_callables,
    walk_from_matches,
)
from endorlabs.workflows.aisast_callgraph.precheck import (
    PrecheckResult,
    precheck_aisast_and_callgraph,
)
from endorlabs.workflows.aisast_callgraph.seeds import (
    ENTRY_POINT_QUERY,
    fetch_entry_point_seeds,
)
from endorlabs.workflows.aisast_callgraph.targets import (
    is_vuln_id_shaped,
    path_patterns_for_package,
    resolve_vuln_walk_targets,
)
from endorlabs.workflows.common import WorkflowResult


def _tenant_root(tenant: str, namespace: str) -> str:
    root = (tenant or "").strip()
    if root:
        return root.split(".", 1)[0]
    ns = (namespace or "").strip()
    return ns.split(".", 1)[0] if ns else ""


def _empty_str_any_dict() -> dict[str, Any]:
    return {}


def _empty_dict_list() -> list[dict[str, Any]]:
    return []


def _empty_str_list() -> list[str]:
    return []


@dataclass
class AisastCallgraphBridgeResult(WorkflowResult):
    """Result payload for the AI-SAST → Call Graph bridge."""

    precheck: dict[str, Any] = field(default_factory=_empty_str_any_dict)
    seeds: list[dict[str, Any]] = field(default_factory=_empty_dict_list)
    matches: list[dict[str, Any]] = field(default_factory=_empty_dict_list)
    paths: list[dict[str, Any]] = field(default_factory=_empty_dict_list)
    vuln_targets: list[dict[str, Any]] = field(default_factory=_empty_dict_list)
    warnings: list[str] = field(default_factory=_empty_str_list)
    project_uuid: str | None = None
    project_name: str | None = None
    namespace: str | None = None
    pv_uuid: str | None = None
    pv_name: str | None = None
    query: str = ENTRY_POINT_QUERY
    path_to_resolved: list[str] = field(default_factory=_empty_str_list)

    def as_dict(self) -> dict[str, Any]:
        """JSON-serializable workflow output."""
        return {
            "status": self.status,
            "message": self.message,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "project_uuid": self.project_uuid,
            "project_name": self.project_name,
            "namespace": self.namespace,
            "pv_uuid": self.pv_uuid,
            "pv_name": self.pv_name,
            "query": self.query,
            "precheck": self.precheck,
            "seeds": self.seeds,
            "matches": self.matches,
            "vuln_targets": self.vuln_targets,
            "path_to_resolved": list(self.path_to_resolved),
            "paths": self.paths,
            "seed_count": len(self.seeds),
            "match_hit_count": sum(1 for m in self.matches if m.get("match_count")),
            "path_hit_count": sum(1 for p in self.paths if p.get("path_found")),
            "cg_path_is_not_finding_reachability": True,
            "disclaimer": WALK_DISCLAIMER,
        }


def _merge_path_to(
    explicit: list[str] | None,
    *,
    vuln_targets: list[Any],
) -> list[str]:
    """Prefer explicit --path-to; else first Finding-derived package patterns."""
    cleaned = [
        p.strip()
        for p in (explicit or [])
        if p and str(p).strip() and not is_vuln_id_shaped(str(p).strip())
    ]
    if cleaned:
        return cleaned
    if vuln_targets:
        return list(vuln_targets[0].path_to_patterns)
    return []


def run_aisast_callgraph_bridge(
    client: Any,
    project: Any,
    *,
    tenant: str,
    namespace: str,
    path_to: list[str] | None = None,
    vuln_id: str | None = None,
    finding_package: str | None = None,
    path_to_symbol: str | None = None,
    max_depth: int = 6,
    max_paths: int = 5,
    max_seeds: int = 40,
    max_pages: int = 50,
    page_size: int = 200,
    query: str = ENTRY_POINT_QUERY,
) -> AisastCallgraphBridgeResult:
    """Precheck planes, fetch AI-SAST seeds, match CG nodes, optional safe BFS.

    Walk targets come from ``path_to`` and/or Finding-derived package tokens
    (``vuln_id`` / ``finding_package``). Advisory ids are never CG URI patterns.
    """
    project_ns = namespace
    meta = getattr(project, "meta", None)
    project_name = str(getattr(meta, "name", "") or "") if meta else ""
    project_uuid = str(getattr(project, "uuid", "") or "")
    tenant_root = _tenant_root(tenant, project_ns)

    pre: PrecheckResult = precheck_aisast_and_callgraph(
        client,
        project,
        tenant_root=tenant_root,
        namespace=project_ns,
        max_pages=max_pages,
        page_size=page_size,
    )
    result = AisastCallgraphBridgeResult(
        project_uuid=project_uuid or None,
        project_name=project_name or None,
        namespace=project_ns,
        query=query,
        precheck=pre.as_dict(),
    )
    if not pre.ok:
        failed = ", ".join(pre.failed_gate_ids()) or "unknown"
        result.status = "error"
        result.message = f"Precheck failed: {failed}"
        result.errors = [g.message for g in pre.gates if not g.ok]
        return result

    assert pre.vector_store is not None
    assert pre.decoded is not None
    assert pre.package_version is not None

    pv = pre.package_version
    result.pv_uuid = getattr(pv, "uuid", None)
    if pv.meta and getattr(pv.meta, "name", None):
        result.pv_name = str(pv.meta.name)
    else:
        result.pv_name = result.pv_uuid

    seeds = fetch_entry_point_seeds(
        client,
        pre.vector_store,
        repo_name=pre.repo_name or project_name,
        query=query,
        max_seeds=max_seeds,
    )
    result.seeds = [
        {
            "fqn": s.get("fqn"),
            "file_path": s.get("file_path"),
            "line_start": s.get("line_start"),
            "line_end": s.get("line_end"),
            "rest_path": s.get("rest_path"),
            "is_entry_point": s.get("is_entry_point"),
            "is_source": s.get("is_source"),
            "is_sink": s.get("is_sink"),
            "score": s.get("score"),
            "data_snippet": s.get("data_snippet"),
        }
        for s in seeds
    ]
    if not seeds:
        result.warnings.append(
            "function_summary query returned no seeds for this repo; "
            "try a broader --query or confirm AI-SAST indexing."
        )

    callables = list(pre.decoded.callables or [])
    edges = list(pre.decoded.edges or [])
    matches = match_seeds_to_callables(seeds, callables)
    result.matches = matches

    want_walk = bool(path_to) or bool(vuln_id) or bool(finding_package)
    vuln_targets: list[Any] = []
    if want_walk and (vuln_id or finding_package or not path_to):
        try:
            vuln_targets = resolve_vuln_walk_targets(
                client,
                project,
                namespace=project_ns,
                vuln_id=vuln_id,
                package_substring=finding_package,
                symbol=path_to_symbol,
                max_pages=1,
            )
        except Exception as exc:
            result.warnings.append(
                f"Finding target resolution failed ({type(exc).__name__}); "
                "continuing with explicit --path-to only."
            )
    result.vuln_targets = [t.as_dict() for t in vuln_targets]

    # Explicit path-to wins; optional symbol AND when package-only explicit token
    explicit = list(path_to or [])
    if explicit and path_to_symbol and len(explicit) == 1:
        explicit = path_patterns_for_package(explicit[0], symbol=path_to_symbol)

    path_to_patterns = _merge_path_to(explicit, vuln_targets=vuln_targets)
    result.path_to_resolved = path_to_patterns

    if want_walk and not path_to_patterns:
        result.warnings.append(
            "No CG path-to patterns resolved (advisory ids are not URI "
            "patterns; pass --path-to <package> or --vuln / --finding-package)."
        )

    if path_to_patterns:
        result.paths = walk_from_matches(
            callables,
            edges,
            matches,
            path_to=path_to_patterns,
            max_depth=max_depth,
            max_paths=max_paths,
        )

    hit = sum(1 for m in matches if m.get("match_count"))
    result.status = "success"
    if path_to_patterns:
        path_hits = sum(1 for p in result.paths if p.get("path_found"))
        result.message = (
            f"Matched {hit}/{len(matches)} AI-SAST seeds to CG nodes; "
            f"{path_hits} path(s) found to {path_to_patterns!r}. "
            f"{WALK_DISCLAIMER}"
        )
    else:
        result.message = (
            f"Matched {hit}/{len(matches)} AI-SAST seeds to CG nodes "
            "(pass --path-to or --vuln / --finding-package to BFS-walk)."
        )
    return result
