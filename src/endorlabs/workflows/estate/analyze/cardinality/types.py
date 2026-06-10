"""Result types for analytics version-cardinality export."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.estate.analyze.cardinality.tabular import TabularExport


@dataclass
class VersionCardinalityStats:
    """Aggregated statistics for a version-cardinality export."""

    estate_root: str = ""
    namespace_count: int = 0
    project_count: int = 0
    importer_package_version_count: int = 0
    package_count: int = 0
    name_version_group_count: int = 0
    max_version_cardinality: int = 0
    total_dependency_usage_rows: int = 0


@dataclass
class VersionCardinalityResult(WorkflowResult):
    """Version cardinality rollup plus optional name-by-version usage detail."""

    stats: VersionCardinalityStats = field(default_factory=VersionCardinalityStats)
    table: TabularExport = field(default_factory=TabularExport)
    usage_by_name_version: TabularExport = field(default_factory=TabularExport)

    @property
    def rows(self) -> list[dict[str, object]]:
        """Cardinality rollup rows (alias for ``table.rows``)."""
        return self.table.rows


@dataclass
class RiskRankedCardinalityStats:
    """Aggregated statistics for risk-ranked version cardinality."""

    estate_root: str = ""
    project_count: int = 0
    finding_count: int = 0
    ranked_package_count: int = 0
    top_n: int = 0
    namespace_count: int = 0


@dataclass
class RiskRankedCardinalityResult(WorkflowResult):
    """Risk-ranked package list plus top-N version cardinality with risk metadata."""

    stats: RiskRankedCardinalityStats = field(
        default_factory=RiskRankedCardinalityStats
    )
    ranking_table: TabularExport = field(default_factory=TabularExport)
    version_detail_table: TabularExport = field(default_factory=TabularExport)
    document: dict[str, Any] = field(default_factory=dict)


# Backward-compatible aliases for earlier estate-export naming.
EstateDependencyExportStats = VersionCardinalityStats
EstateDependencyExportResult = VersionCardinalityResult
