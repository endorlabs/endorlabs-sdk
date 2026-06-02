"""Result types for analytics version-cardinality export."""

from __future__ import annotations

from dataclasses import dataclass, field

from endorlabs.utils.tabular import TabularExport

from ..common import WorkflowResult


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


# Backward-compatible aliases for earlier estate-export naming.
EstateDependencyExportStats = VersionCardinalityStats
EstateDependencyExportResult = VersionCardinalityResult
