"""Orchestrate report packet cube construction."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from endorlabs.tools.list_sharding import ProjectShard
from endorlabs.workflows.reports.analyze.code_findings_trend import (
    build_code_findings_burndown_report,
)
from endorlabs.workflows.reports.analyze.findings_trend import (
    build_sca_burndown_report,
)
from endorlabs.workflows.reports.analyze.patches import (
    collect_patches_report,
    empty_patches_report,
)
from endorlabs.workflows.reports.analyze.projects import (
    build_onboarding_report,
    discover_projects,
)
from endorlabs.workflows.reports.analyze.sprawl import (
    build_version_sprawl_report,
    collect_leaf_pairs,
)
from endorlabs.workflows.reports.logging import logger, milestone
from endorlabs.workflows.reports.schemas.packet_v0 import REPORT_PACKET_SCHEMA

if TYPE_CHECKING:
    from endorlabs import Client

_WF = "packet"


def _elapsed_s(t0: float) -> str:
    return f"{time.perf_counter() - t0:.1f}"


def _projects_to_shards(projects: list[dict[str, Any]]) -> list[ProjectShard]:
    """Map packet discover rows to Finding list shards."""
    out: list[ProjectShard] = []
    for project in projects:
        uid = str(project.get("uuid") or "")
        ns = str(project.get("namespace") or "")
        if uid and ns:
            out.append(ProjectShard(project_uuid=uid, namespace=ns))
    return out


def _empty_sca_burndown(
    *,
    lookback: int,
    min_projects: int,
    max_workers: int,
    tag_catalog: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "findingCriteria": "",
        "lookback": lookback,
        "interval": "week",
        "seriesFilters": {"perPath": {}},
        "tagSeries": {"tags": [], "perTag": {}},
        "tagSeriesMeta": {
            "seriesReady": [],
            "seriesPending": [e["tag"] for e in tag_catalog],
            "seriesReadyCount": 0,
            "seriesPendingCount": len(tag_catalog),
            "pullPolicy": {
                "minProjects": min_projects,
                "mode": "skipped",
                "workers": max_workers,
            },
        },
        "throughput": {"windows": {}, "perPath": {}, "perTag": {}},
    }


def _empty_code_findings(
    *,
    lookback: int,
    min_projects: int,
    max_workers: int,
    tag_catalog: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "lookback": lookback,
        "interval": "week",
        "periodCaption": "",
        "categories": ["sast", "ai_sast", "secrets"],
        "byCategory": {},
        "tagSeriesMeta": {
            "seriesReady": [],
            "seriesPending": [e["tag"] for e in tag_catalog],
            "seriesReadyCount": 0,
            "seriesPendingCount": len(tag_catalog),
            "pullPolicy": {
                "minProjects": min_projects,
                "mode": "skipped",
                "workers": max_workers,
            },
        },
    }


def _empty_sprawl() -> dict[str, Any]:
    return {
        "histKeys": [],
        "ecosystems": [],
        "estate": {},
        "perPath": {},
        "perTag": {},
    }


def _run_slice[T](
    name: str,
    reports_meta: dict[str, Any],
    empty: T,
    fn: Callable[[], T],
) -> T:
    """Run one report slice; on failure record gap and return *empty*."""
    try:
        value = fn()
        reports_meta[name] = {"status": "ok"}
        return value
    except Exception as exc:
        err = type(exc).__name__
        reports_meta[name] = {"status": "failed", "error_type": err}
        logger.warning("%s", f"{_WF}.{name}.failed error_type={err}")
        milestone(_WF, f"{name}.failed", error_type=err)
        return empty


def build_report_packet(
    client: Client,
    namespace: str,
    *,
    lookback: int = 13,
    min_projects: int = 1,
    max_workers: int = 24,
    traverse: bool = True,
    include_version_sprawl: bool = True,
    include_findings_burndown: bool = True,
    include_sca_burndown: bool | None = None,
    include_code_findings_burndown: bool = True,
    include_patches: bool = True,
    patches_only: bool = False,
    patches_workers: int | None = None,
) -> dict[str, Any]:
    """Build a portable ``endor.report_packet.v0`` cube for *namespace*.

    Library entrypoint: ``Client`` in → cube dict out (no file I/O).

    ``include_findings_burndown`` is a compat alias for ``include_sca_burndown``.

    When *patches_only* is true, skip onboarding/sprawl/burndown pulls and build
    only ``reports.patches`` (campaign batch path).

    Each report slice is isolated: a timeout in SCA (etc.) still yields a cube
    with other slices filled and ``dataGaps`` / ``reportsMeta`` recording the
    failure. Discover failure remains fatal.

    Progress: INFO milestones via :mod:`endorlabs.workflows.reports.logging`
    (configure a StreamHandler in the CLI to surface them on stdout).
    """
    if include_sca_burndown is None:
        include_sca_burndown = include_findings_burndown

    patch_workers = int(patches_workers if patches_workers is not None else max_workers)
    wall0 = time.perf_counter()
    reports_meta: dict[str, Any] = {}
    milestone(
        _WF,
        "start",
        patches_only=int(patches_only),
        sprawl=int(include_version_sprawl and not patches_only),
        sca=int(include_sca_burndown and not patches_only),
        code=int(include_code_findings_burndown and not patches_only),
        patches=int(include_patches or patches_only),
        lookback=lookback,
        workers=max_workers,
    )

    if patches_only:
        t0 = time.perf_counter()
        milestone(_WF, "patches.start", mode="patches_only", workers=patch_workers)
        patches = _run_slice(
            "patches",
            reports_meta,
            empty_patches_report(),
            lambda: collect_patches_report(
                client, namespace, max_workers=max(1, min(patch_workers, 16))
            ),
        )
        if reports_meta.get("patches", {}).get("status") == "ok":
            milestone(
                _WF,
                "patches.done",
                mode="patches_only",
                elapsed_s=_elapsed_s(t0),
            )
        empty_sca = _empty_sca_burndown(
            lookback=lookback,
            min_projects=min_projects,
            max_workers=max_workers,
            tag_catalog=[],
        )
        empty_code = _empty_code_findings(
            lookback=lookback,
            min_projects=min_projects,
            max_workers=max_workers,
            tag_catalog=[],
        )
        data_gaps = [
            key for key, meta in reports_meta.items() if meta.get("status") == "failed"
        ]
        milestone(_WF, "done", mode="patches_only", elapsed_s=_elapsed_s(wall0))
        return {
            "schema": REPORT_PACKET_SCHEMA,
            "tenant": namespace,
            "pulledAt": datetime.now(UTC).isoformat(),
            "pathOptions": ["all", namespace],
            "leafNamespaces": [namespace],
            "tagCatalog": [],
            "tagSeriesMeta": empty_sca.get("tagSeriesMeta"),
            "reportsMeta": reports_meta,
            "dataGaps": data_gaps,
            "reports": {
                "onboarding": {
                    "projects": [],
                    "projectCount": 0,
                    "cadence": {},
                },
                "versionSprawl": _empty_sprawl(),
                "scaBurndown": empty_sca,
                "codeFindingsBurndown": empty_code,
                "patches": patches,
            },
        }

    t0 = time.perf_counter()
    milestone(_WF, "discover.start", traverse=int(traverse))
    discovered = discover_projects(client, namespace, traverse=traverse)
    projects = discovered["projects"]
    tag_catalog = discovered["tagCatalog"]
    path_options = discovered["pathOptions"]
    leaves = discovered["leafNamespaces"] or [namespace]
    project_shards = _projects_to_shards(projects)
    milestone(
        _WF,
        "discover.done",
        projects=len(projects),
        leaves=len(leaves),
        tags=len(tag_catalog),
        paths=len(path_options),
        elapsed_s=_elapsed_s(t0),
    )

    t0 = time.perf_counter()
    milestone(_WF, "onboarding.start")
    onboarding = build_onboarding_report(projects)
    onboarding["projects"] = [
        {
            "uuid": str(p.get("uuid") or ""),
            "name": str(p.get("name") or ""),
            "namespace": str(p.get("namespace") or ""),
            "tags": list(p.get("tags") or []),
            "create_time": str(p.get("create_time") or ""),
        }
        for p in projects
        if p.get("uuid")
    ]

    def _cadence() -> dict[str, Any]:
        from endorlabs.workflows.reports.analyze.onboarding_cadence import (
            collect_onboarding_cadence,
        )

        t_cadence = time.perf_counter()
        milestone(_WF, "cadence.start")
        cadence = collect_onboarding_cadence(
            client,
            tenant=namespace,
            projects=projects,
            leaf_namespaces=leaves,
            tag_catalog=tag_catalog,
        )
        milestone(_WF, "cadence.done", elapsed_s=_elapsed_s(t_cadence))
        return cadence

    onboarding["cadence"] = _run_slice("cadence", reports_meta, {}, _cadence)
    milestone(
        _WF,
        "onboarding.done",
        projects=int(onboarding.get("projectCount") or len(projects)),
        elapsed_s=_elapsed_s(t0),
    )

    version_sprawl = _empty_sprawl()
    if include_version_sprawl and leaves:

        def _sprawl() -> dict[str, Any]:
            t_sp = time.perf_counter()
            milestone(_WF, "sprawl.start", leaves=len(leaves))
            leaf_pairs = collect_leaf_pairs(client, leaves)
            built = build_version_sprawl_report(
                leaf_pairs=leaf_pairs,
                path_options=path_options,
                projects=projects,
                tag_catalog=tag_catalog,
            )
            milestone(
                _WF,
                "sprawl.done",
                ecosystems=len(built.get("ecosystems") or []),
                elapsed_s=_elapsed_s(t_sp),
            )
            return built

        version_sprawl = _run_slice(
            "versionSprawl", reports_meta, _empty_sprawl(), _sprawl
        )
    else:
        milestone(_WF, "sprawl.skipped")
        reports_meta["versionSprawl"] = {"status": "skipped"}

    sca = _empty_sca_burndown(
        lookback=lookback,
        min_projects=min_projects,
        max_workers=max_workers,
        tag_catalog=tag_catalog,
    )
    if include_sca_burndown and leaves:

        def _sca() -> dict[str, Any]:
            t_sca = time.perf_counter()
            milestone(
                _WF,
                "sca_burndown.start",
                lookback=lookback,
                workers=max_workers,
                leaves=len(leaves),
            )
            built = build_sca_burndown_report(
                client,
                tenant=namespace,
                projects=projects,
                leaf_namespaces=leaves,
                path_options=path_options,
                tag_catalog=tag_catalog,
                lookback=lookback,
                min_projects=min_projects,
                max_workers=max_workers,
            )
            meta = built.get("tagSeriesMeta") or {}
            milestone(
                _WF,
                "sca_burndown.done",
                tags_ready=int(meta.get("seriesReadyCount") or 0),
                elapsed_s=_elapsed_s(t_sca),
            )
            return built

        sca = _run_slice(
            "scaBurndown",
            reports_meta,
            sca,
            _sca,
        )
    else:
        milestone(_WF, "sca_burndown.skipped")
        reports_meta["scaBurndown"] = {"status": "skipped"}

    code = _empty_code_findings(
        lookback=lookback,
        min_projects=min_projects,
        max_workers=max_workers,
        tag_catalog=tag_catalog,
    )
    if include_code_findings_burndown and leaves:

        def _code() -> dict[str, Any]:
            t_code = time.perf_counter()
            milestone(
                _WF,
                "code_burndown.start",
                lookback=lookback,
                workers=max_workers,
                leaves=len(leaves),
            )
            built = build_code_findings_burndown_report(
                client,
                tenant=namespace,
                projects=projects,
                leaf_namespaces=leaves,
                path_options=path_options,
                tag_catalog=tag_catalog,
                lookback=lookback,
                min_projects=min_projects,
                max_workers=max_workers,
            )
            meta = built.get("tagSeriesMeta") or {}
            milestone(
                _WF,
                "code_burndown.done",
                tags_ready=int(meta.get("seriesReadyCount") or 0),
                elapsed_s=_elapsed_s(t_code),
            )
            return built

        code = _run_slice(
            "codeFindingsBurndown",
            reports_meta,
            code,
            _code,
        )
    else:
        milestone(_WF, "code_burndown.skipped")
        reports_meta["codeFindingsBurndown"] = {"status": "skipped"}

    patches = empty_patches_report()
    if include_patches:

        def _patches() -> dict[str, Any]:
            t_p = time.perf_counter()
            milestone(_WF, "patches.start", workers=patch_workers)
            built = collect_patches_report(
                client,
                namespace,
                max_workers=max(1, min(patch_workers, 16)),
                shards=project_shards,
            )
            milestone(_WF, "patches.done", elapsed_s=_elapsed_s(t_p))
            return built

        patches = _run_slice(
            "patches",
            reports_meta,
            empty_patches_report(),
            _patches,
        )
    else:
        milestone(_WF, "patches.skipped")
        reports_meta["patches"] = {"status": "skipped"}

    data_gaps = [
        key for key, meta in reports_meta.items() if meta.get("status") == "failed"
    ]
    milestone(
        _WF,
        "done",
        elapsed_s=_elapsed_s(wall0),
        data_gaps=len(data_gaps),
    )
    return {
        "schema": REPORT_PACKET_SCHEMA,
        "tenant": namespace,
        "pulledAt": datetime.now(UTC).isoformat(),
        "pathOptions": path_options,
        "leafNamespaces": leaves,
        "tagCatalog": tag_catalog,
        "tagSeriesMeta": sca.get("tagSeriesMeta"),
        "reportsMeta": reports_meta,
        "dataGaps": data_gaps,
        "reports": {
            "onboarding": onboarding,
            "versionSprawl": version_sprawl,
            # Readers fall back to the legacy "findingsBurndown" key for cubes
            # built before the rename; new cubes carry the slice once.
            "scaBurndown": sca,
            "codeFindingsBurndown": code,
            "patches": patches,
        },
    }


def upsert_code_findings_burndown(
    client: Client,
    cube: dict[str, Any],
    *,
    lookback: int | None = None,
    min_projects: int = 1,
    max_workers: int = 24,
    traverse: bool = True,
) -> dict[str, Any]:
    """Rebuild only ``reports.codeFindingsBurndown`` into an existing packet cube.

    Reuses onboarding / sprawl / SCA slices already on *cube*. Still rediscovers
    projects (needed for tagged-project matrices) but skips sprawl and SCA
    FindingLog pulls.
    """
    namespace = str(cube.get("tenant") or "")
    if not namespace:
        raise ValueError("cube missing tenant")

    wall0 = time.perf_counter()
    milestone(_WF, "upsert_code.start")

    reports = cube.setdefault("reports", {})
    sca = reports.get("scaBurndown") or reports.get("findingsBurndown") or {}
    resolved_lookback = int(
        lookback
        if lookback is not None
        else (sca.get("lookback") or cube.get("lookback") or 13)
    )

    t0 = time.perf_counter()
    milestone(_WF, "discover.start", traverse=int(traverse), mode="upsert_code")
    discovered = discover_projects(client, namespace, traverse=traverse)
    projects = discovered["projects"]
    tag_catalog = discovered["tagCatalog"]
    path_options = discovered["pathOptions"]
    leaves = discovered["leafNamespaces"] or [namespace]
    milestone(
        _WF,
        "discover.done",
        mode="upsert_code",
        projects=len(projects),
        leaves=len(leaves),
        tags=len(tag_catalog),
        elapsed_s=_elapsed_s(t0),
    )

    code = _empty_code_findings(
        lookback=resolved_lookback,
        min_projects=min_projects,
        max_workers=max_workers,
        tag_catalog=tag_catalog,
    )
    reports_meta = dict(cube.get("reportsMeta") or {})
    if leaves:

        def _code() -> dict[str, Any]:
            t_code = time.perf_counter()
            milestone(
                _WF,
                "code_burndown.start",
                mode="upsert_code",
                lookback=resolved_lookback,
                workers=max_workers,
            )
            built = build_code_findings_burndown_report(
                client,
                tenant=namespace,
                projects=projects,
                leaf_namespaces=leaves,
                path_options=path_options,
                tag_catalog=tag_catalog,
                lookback=resolved_lookback,
                min_projects=min_projects,
                max_workers=max_workers,
            )
            milestone(
                _WF,
                "code_burndown.done",
                mode="upsert_code",
                elapsed_s=_elapsed_s(t_code),
            )
            return built

        code = _run_slice(
            "codeFindingsBurndown",
            reports_meta,
            code,
            _code,
        )
    else:
        milestone(_WF, "code_burndown.skipped", mode="upsert_code")
        reports_meta["codeFindingsBurndown"] = {"status": "skipped"}

    # Refresh topology fields used by HTML filters; keep other report slices.
    cube["pathOptions"] = path_options
    cube["leafNamespaces"] = leaves
    cube["tagCatalog"] = tag_catalog
    cube["pulledAt"] = datetime.now(UTC).isoformat()
    reports["codeFindingsBurndown"] = code
    cube["reportsMeta"] = reports_meta
    cube["dataGaps"] = [
        key for key, meta in reports_meta.items() if meta.get("status") == "failed"
    ]
    milestone(_WF, "upsert_code.done", elapsed_s=_elapsed_s(wall0))
    return cube
