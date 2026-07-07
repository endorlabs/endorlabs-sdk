"""Topology → validate → Query recipes for estate dashboard counts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from endorlabs.query import OutputShape, recommend
from endorlabs.utils.artifact_io import write_json
from endorlabs.workflows.estate.workspace.paths import ir_path

if TYPE_CHECKING:
    from endorlabs import Client

ONLINE_DASHBOARD_SCHEMA = "endor.online_dashboard_counts.v1"


@dataclass
class OnlineDashboardCounts:
    """Query-backed per-project counts for estate dashboard tiles."""

    tenant: str
    archetype: str
    project_count: int
    pv_counts: dict[str, int] = field(default_factory=dict)
    finding_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    dm_counts: dict[str, int] = field(default_factory=dict)
    routing: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for ``ir/online_dashboard_counts.json``."""
        return {
            "schema": ONLINE_DASHBOARD_SCHEMA,
            "generated_at": datetime.now(UTC).isoformat(),
            "tenant": self.tenant,
            "archetype": self.archetype,
            "project_count": self.project_count,
            "pv_counts": self.pv_counts,
            "finding_counts": self.finding_counts,
            "dm_counts": self.dm_counts,
            "routing": self.routing,
            "validation": self.validation,
            "totals": {
                "pv": sum(self.pv_counts.values()),
                "dm": sum(self.dm_counts.values()),
                "findings": {
                    label: sum(
                        cats.get(label, 0) for cats in self.finding_counts.values()
                    )
                    for label in ("VULNERABILITY", "SECRETS", "MALWARE")
                },
            },
        }


def fetch_online_dashboard_counts(
    client: Client,
    namespace: str,
    *,
    traverse: bool = True,
    max_pages: int | None = None,
    validate: bool = True,
    sample_size: int = 5,
) -> OnlineDashboardCounts:
    """Discover topology, optionally validate, and fetch Query count recipes."""
    topology = client.Query.Project.discover(
        namespace,
        traverse=traverse,
        max_pages=max_pages,
    )
    projects = topology.projects
    plan = recommend(OutputShape.COUNT_BY_PROJECT, topology=topology)
    validation_payload: dict[str, Any] = {}
    if validate and projects:
        sample = projects[:sample_size]
        validation_payload["pv"] = client.Query.Project.validate_sample(
            sample, recipe="pv", sample_size=sample_size
        ).to_dict()
        validation_payload["findings"] = client.Query.Project.validate_sample(
            sample, recipe="findings", sample_size=sample_size
        ).to_dict()
        validation_payload["dm"] = client.Query.Project.validate_sample(
            sample, recipe="dm", sample_size=sample_size
        ).to_dict()
    project_query = client.Query.Project
    return OnlineDashboardCounts(
        tenant=topology.tenant,
        archetype=topology.archetype,
        project_count=topology.project_count,
        pv_counts=project_query.count_pv(projects) if projects else {},
        finding_counts=project_query.count_findings_by_category(projects)
        if projects
        else {},
        dm_counts=project_query.count_dm(projects) if projects else {},
        routing=plan.to_dict(),
        validation=validation_payload,
    )


def write_online_dashboard_artifact(
    workspace_root: Path,
    counts: OnlineDashboardCounts,
) -> Path:
    """Write online Query counts beside disk IR artifacts."""
    out = ir_path(workspace_root, "online_dashboard_counts.json")
    write_json(str(out), counts.to_dict(), base_dir=workspace_root)
    return out


def load_online_dashboard_counts(workspace_root: Path) -> dict[str, Any] | None:
    """Load persisted online counts when present."""
    import json

    path = ir_path(workspace_root, "online_dashboard_counts.json")
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None
