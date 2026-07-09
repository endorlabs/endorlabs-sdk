"""Recommend Query vs facade fetch strategies from topology and output shape."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .topology import TopologySnapshot

PrimaryPath = Literal[
    "query",
    "facade_count",
    "facade_list_groups",
    "facade_list",
]
ShardKey = Literal["project", "leaf_namespace", "tenant"]


class OutputShape(StrEnum):
    """What the caller needs from an estate-scale fetch."""

    COUNT_BY_PROJECT = "count_by_project"
    FINDING_ROWS = "finding_rows"
    FINDING_CATEGORY_COUNTS = "finding_category_counts"
    FINDING_LOG_TRENDS = "finding_log_trends"
    DM_VERSION_CARDINALITY = "dm_version_cardinality"
    OSS_COORDINATE_LOOKUP = "oss_coordinate_lookup"
    TENANT_FINDING_TOTALS = "tenant_finding_totals"


@dataclass(frozen=True, slots=True)
class QueryPlan:
    """Non-executing routing recommendation."""

    output_shape: OutputShape
    primary: PrimaryPath
    shard_key: ShardKey
    validate_recommended: bool
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, str | bool | tuple[str, ...]]:
        """Serialize the plan for logging or artifacts."""
        return {
            "output_shape": self.output_shape.value,
            "primary": self.primary,
            "shard_key": self.shard_key,
            "validate_recommended": self.validate_recommended,
            "notes": self.notes,
        }


def recommend(
    output_shape: OutputShape,
    *,
    topology: TopologySnapshot | None = None,
) -> QueryPlan:
    """Return a fetch plan for ``output_shape`` and optional topology signals."""
    if output_shape == OutputShape.FINDING_LOG_TRENDS:
        return QueryPlan(
            output_shape=output_shape,
            primary="facade_list_groups",
            shard_key="tenant",
            validate_recommended=False,
            notes=(
                "No shipped SDK recipe; FindingLog.list_groups is workflow default.",
                "Query.create does not support group_by_time; use facade list_groups.",
                "Aggregate-first; shard per project on timeout.",
            ),
        )
    if output_shape == OutputShape.DM_VERSION_CARDINALITY:
        return QueryPlan(
            output_shape=output_shape,
            primary="facade_list_groups",
            shard_key="leaf_namespace",
            validate_recommended=False,
            notes=(
                "Per-project DM count joins differ from version-bucket group rollups.",
                "Root QuerySpec.root('DependencyMetadata').group(...) "
                "validated for buckets.",
                "Use DependencyMetadata.list_groups per child namespace, "
                "or root Query group.",
                "Do not use Query.Project.count_dm for version cardinality.",
            ),
        )
    if output_shape == OutputShape.OSS_COORDINATE_LOOKUP:
        return QueryPlan(
            output_shape=output_shape,
            primary="facade_list",
            shard_key="tenant",
            validate_recommended=False,
            notes=(
                "Use QueryVulnerability or QueryMalware (oss scope), not Query.create.",
            ),
        )
    if output_shape in (
        OutputShape.FINDING_ROWS,
        OutputShape.TENANT_FINDING_TOTALS,
    ):
        notes: tuple[str, ...]
        if output_shape == OutputShape.TENANT_FINDING_TOTALS:
            notes = (
                "No per-project grain: probe Query.at_namespace with "
                "QuerySpec.root('Finding').list_parameters(count=True) at leaf "
                "namespace, or facade Finding.count with selective filter and bounds.",
                "Per-project breakdown: Query.Project.collect after validate_sample.",
                "Fallback: Finding.list or list_for_shards when rows needed.",
            )
        else:
            notes = (
                "Masked per-project row export: Query.Project.collect with estate "
                "or PRF list specs after validate_sample.",
                "Fallback: Finding.list_by_project or list_for_shards.",
            )
        return QueryPlan(
            output_shape=output_shape,
            primary="query",
            shard_key="project",
            validate_recommended=True,
            notes=notes,
        )

    if output_shape == OutputShape.FINDING_CATEGORY_COUNTS:
        return _recommend_query_counts(
            output_shape,
            topology=topology,
            notes_prefix=(
                "Use client.Query.Project.count_findings_by_category "
                "after validate_sample."
            ),
        )

    return _recommend_query_counts(
        OutputShape.COUNT_BY_PROJECT,
        topology=topology,
        notes_prefix="Use client.Query.Project.count_pv after validate_sample.",
    )


def _recommend_query_counts(
    output_shape: OutputShape,
    *,
    topology: TopologySnapshot | None,
    notes_prefix: str,
) -> QueryPlan:
    shard_key: ShardKey = "project"
    validate = True
    notes: list[str] = [notes_prefix]

    if topology is not None:
        if topology.archetype == "single_repo":
            return QueryPlan(
                output_shape=output_shape,
                primary="facade_count",
                shard_key="project",
                validate_recommended=True,
                notes=(
                    notes_prefix,
                    "Single-repo: facade count is acceptable; Query optional.",
                ),
            )
        if topology.archetype == "monorepo_hub":
            shard_key = "leaf_namespace"
            notes.append("Monorepo hub: Query per leaf namespace with pagination.")
        elif topology.archetype in ("managed_platform", "estate_sprawl"):
            shard_key = "leaf_namespace"
            notes.append(
                "Many leaf namespaces: Query reduces round-trips for validated joins."
            )
        if topology.duplicate_name_groups:
            notes.append(
                "Duplicate meta.name across namespaces; disambiguate by wire namespace."
            )

    return QueryPlan(
        output_shape=output_shape,
        primary="query",
        shard_key=shard_key,
        validate_recommended=validate,
        notes=tuple(notes),
    )
