"""Orchestrate report packet cube construction."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from endorlabs.workflows.reports.analyze.code_findings_trend import (
    build_code_findings_burndown_report,
)
from endorlabs.workflows.reports.analyze.findings_trend import (
    build_sca_burndown_report,
)
from endorlabs.workflows.reports.analyze.projects import (
    build_onboarding_report,
    discover_projects,
)
from endorlabs.workflows.reports.analyze.sprawl import (
    build_version_sprawl_report,
    collect_leaf_pairs,
)
from endorlabs.workflows.reports.schemas.packet_v0 import REPORT_PACKET_SCHEMA

if TYPE_CHECKING:
    from endorlabs import Client


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
) -> dict[str, Any]:
    """Build a portable ``endor.report_packet.v0`` cube for *namespace*.

    Library entrypoint: ``Client`` in → cube dict out (no file I/O).

    ``include_findings_burndown`` is a compat alias for ``include_sca_burndown``.
    """
    if include_sca_burndown is None:
        include_sca_burndown = include_findings_burndown

    discovered = discover_projects(client, namespace, traverse=traverse)
    projects = discovered["projects"]
    tag_catalog = discovered["tagCatalog"]
    path_options = discovered["pathOptions"]
    leaves = discovered["leafNamespaces"] or [namespace]

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

        onboarding["cadence"] = collect_onboarding_cadence(
            client,
            tenant=namespace,
            projects=projects,
            leaf_namespaces=leaves,
            tag_catalog=tag_catalog,
        )
    except Exception:
        onboarding["cadence"] = {}

    version_sprawl: dict[str, Any] = {
        "histKeys": [],
        "ecosystems": [],
        "estate": {},
        "perPath": {},
        "perTag": {},
    }
    if include_version_sprawl and leaves:
        leaf_pairs = collect_leaf_pairs(client, leaves)
        version_sprawl = build_version_sprawl_report(
            leaf_pairs=leaf_pairs,
            path_options=path_options,
            projects=projects,
            tag_catalog=tag_catalog,
        )

    sca = _empty_sca_burndown(
        lookback=lookback,
        min_projects=min_projects,
        max_workers=max_workers,
        tag_catalog=tag_catalog,
    )
    if include_sca_burndown and leaves:
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

    code = _empty_code_findings(
        lookback=lookback,
        min_projects=min_projects,
        max_workers=max_workers,
        tag_catalog=tag_catalog,
    )
    if include_code_findings_burndown and leaves:
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
            "scaBurndown": sca,
            # Legacy key for older readers / parity baselines.
            "findingsBurndown": sca,
            "codeFindingsBurndown": code,
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

    reports = cube.setdefault("reports", {})
    sca = reports.get("scaBurndown") or reports.get("findingsBurndown") or {}
    resolved_lookback = int(
        lookback
        if lookback is not None
        else (sca.get("lookback") or cube.get("lookback") or 13)
    )

    discovered = discover_projects(client, namespace, traverse=traverse)
    projects = discovered["projects"]
    tag_catalog = discovered["tagCatalog"]
    path_options = discovered["pathOptions"]
    leaves = discovered["leafNamespaces"] or [namespace]

    code = _empty_code_findings(
        lookback=resolved_lookback,
        min_projects=min_projects,
        max_workers=max_workers,
        tag_catalog=tag_catalog,
    )
    if leaves:
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

    # Refresh topology fields used by HTML filters; keep other report slices.
    cube["pathOptions"] = path_options
    cube["leafNamespaces"] = leaves
    cube["tagCatalog"] = tag_catalog
    cube["pulledAt"] = datetime.now(UTC).isoformat()
    reports["codeFindingsBurndown"] = code
    return cube
