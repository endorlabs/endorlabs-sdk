"""Orchestrate report packet cube construction."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

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

    Progress: INFO milestones via :mod:`endorlabs.workflows.reports.logging`
    (configure a StreamHandler in the CLI to surface them on stdout).
    """
    if include_sca_burndown is None:
        include_sca_burndown = include_findings_burndown

    patch_workers = int(patches_workers if patches_workers is not None else max_workers)
    wall0 = time.perf_counter()
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
        patches = collect_patches_report(
            client, namespace, max_workers=max(1, min(patch_workers, 16))
        )
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
        milestone(_WF, "done", mode="patches_only", elapsed_s=_elapsed_s(wall0))
        return {
            "schema": REPORT_PACKET_SCHEMA,
            "tenant": namespace,
            "pulledAt": datetime.now(UTC).isoformat(),
            "pathOptions": ["all", namespace],
            "leafNamespaces": [namespace],
            "tagCatalog": [],
            "tagSeriesMeta": empty_sca.get("tagSeriesMeta"),
            "reports": {
                "onboarding": {
                    "projects": [],
                    "projectCount": 0,
                    "cadence": {},
                },
                "versionSprawl": {
                    "histKeys": [],
                    "ecosystems": [],
                    "estate": {},
                    "perPath": {},
                    "perTag": {},
                },
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
    try:
        from endorlabs.workflows.reports.analyze.onboarding_cadence import (
            collect_onboarding_cadence,
        )

        t_cadence = time.perf_counter()
        milestone(_WF, "cadence.start")
        onboarding["cadence"] = collect_onboarding_cadence(
            client,
            tenant=namespace,
            projects=projects,
            leaf_namespaces=leaves,
            tag_catalog=tag_catalog,
        )
        milestone(_WF, "cadence.done", elapsed_s=_elapsed_s(t_cadence))
    except Exception as exc:
        onboarding["cadence"] = {}
        logger.warning(
            "%s",
            f"{_WF}.cadence.skipped error_type={type(exc).__name__}",
        )
    milestone(
        _WF,
        "onboarding.done",
        projects=int(onboarding.get("projectCount") or len(projects)),
        elapsed_s=_elapsed_s(t0),
    )

    version_sprawl: dict[str, Any] = {
        "histKeys": [],
        "ecosystems": [],
        "estate": {},
        "perPath": {},
        "perTag": {},
    }
    if include_version_sprawl and leaves:
        t0 = time.perf_counter()
        milestone(_WF, "sprawl.start", leaves=len(leaves))
        leaf_pairs = collect_leaf_pairs(client, leaves)
        version_sprawl = build_version_sprawl_report(
            leaf_pairs=leaf_pairs,
            path_options=path_options,
            projects=projects,
            tag_catalog=tag_catalog,
        )
        milestone(
            _WF,
            "sprawl.done",
            ecosystems=len(version_sprawl.get("ecosystems") or []),
            elapsed_s=_elapsed_s(t0),
        )
    else:
        milestone(_WF, "sprawl.skipped")

    sca = _empty_sca_burndown(
        lookback=lookback,
        min_projects=min_projects,
        max_workers=max_workers,
        tag_catalog=tag_catalog,
    )
    if include_sca_burndown and leaves:
        t0 = time.perf_counter()
        milestone(
            _WF,
            "sca_burndown.start",
            lookback=lookback,
            workers=max_workers,
            leaves=len(leaves),
        )
        sca = build_sca_burndown_report(
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
        meta = sca.get("tagSeriesMeta") or {}
        milestone(
            _WF,
            "sca_burndown.done",
            tags_ready=int(meta.get("seriesReadyCount") or 0),
            elapsed_s=_elapsed_s(t0),
        )
    else:
        milestone(_WF, "sca_burndown.skipped")

    code = _empty_code_findings(
        lookback=lookback,
        min_projects=min_projects,
        max_workers=max_workers,
        tag_catalog=tag_catalog,
    )
    if include_code_findings_burndown and leaves:
        t0 = time.perf_counter()
        milestone(
            _WF,
            "code_burndown.start",
            lookback=lookback,
            workers=max_workers,
            leaves=len(leaves),
        )
        code = build_code_findings_burndown_report(
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
        meta = code.get("tagSeriesMeta") or {}
        milestone(
            _WF,
            "code_burndown.done",
            tags_ready=int(meta.get("seriesReadyCount") or 0),
            elapsed_s=_elapsed_s(t0),
        )
    else:
        milestone(_WF, "code_burndown.skipped")

    patches = empty_patches_report()
    if include_patches:
        t0 = time.perf_counter()
        milestone(_WF, "patches.start", workers=patch_workers)
        patches = collect_patches_report(
            client, namespace, max_workers=max(1, min(patch_workers, 16))
        )
        milestone(_WF, "patches.done", elapsed_s=_elapsed_s(t0))
    else:
        milestone(_WF, "patches.skipped")

    milestone(_WF, "done", elapsed_s=_elapsed_s(wall0))
    return {
        "schema": REPORT_PACKET_SCHEMA,
        "tenant": namespace,
        "pulledAt": datetime.now(UTC).isoformat(),
        "pathOptions": path_options,
        "leafNamespaces": leaves,
        "tagCatalog": tag_catalog,
        "tagSeriesMeta": sca.get("tagSeriesMeta"),
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
    if leaves:
        t0 = time.perf_counter()
        milestone(
            _WF,
            "code_burndown.start",
            mode="upsert_code",
            lookback=resolved_lookback,
            workers=max_workers,
        )
        code = build_code_findings_burndown_report(
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
            _WF, "code_burndown.done", mode="upsert_code", elapsed_s=_elapsed_s(t0)
        )
    else:
        milestone(_WF, "code_burndown.skipped", mode="upsert_code")

    # Refresh topology fields used by HTML filters; keep other report slices.
    cube["pathOptions"] = path_options
    cube["leafNamespaces"] = leaves
    cube["tagCatalog"] = tag_catalog
    cube["pulledAt"] = datetime.now(UTC).isoformat()
    reports["codeFindingsBurndown"] = code
    milestone(_WF, "upsert_code.done", elapsed_s=_elapsed_s(wall0))
    return cube
