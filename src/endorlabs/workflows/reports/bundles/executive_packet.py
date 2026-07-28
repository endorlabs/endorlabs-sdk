"""Orchestrate report packet cube construction."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from endorlabs.workflows.reports.analyze.findings_trend import (
    build_findings_burndown_report,
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


def build_report_packet(
    client: Client,
    namespace: str,
    *,
    lookback: int = 13,
    min_projects: int = 5,
    traverse: bool = True,
    include_version_sprawl: bool = True,
    include_findings_burndown: bool = True,
) -> dict[str, Any]:
    """Build a portable ``endor.report_packet.v0`` cube for *namespace*.

    Library entrypoint: ``Client`` in → cube dict out (no file I/O).
    """
    discovered = discover_projects(client, namespace, traverse=traverse)
    projects = discovered["projects"]
    tag_catalog = discovered["tagCatalog"]
    path_options = discovered["pathOptions"]
    leaves = discovered["leafNamespaces"] or [namespace]

    onboarding = build_onboarding_report(projects)

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

    findings: dict[str, Any] = {
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
            "pullPolicy": {"minProjects": min_projects, "mode": "skipped"},
        },
        "throughput": {"windows": {}, "perPath": {}, "perTag": {}},
    }
    if include_findings_burndown and leaves:
        findings = build_findings_burndown_report(
            client,
            tenant=namespace,
            projects=projects,
            leaf_namespaces=leaves,
            path_options=path_options,
            tag_catalog=tag_catalog,
            lookback=lookback,
            min_projects=min_projects,
        )

    return {
        "schema": REPORT_PACKET_SCHEMA,
        "tenant": namespace,
        "pulledAt": datetime.now(UTC).isoformat(),
        "pathOptions": path_options,
        "leafNamespaces": leaves,
        "tagCatalog": tag_catalog,
        "tagSeriesMeta": findings.get("tagSeriesMeta"),
        "reports": {
            "onboarding": onboarding,
            "versionSprawl": version_sprawl,
            "findingsBurndown": findings,
        },
    }
