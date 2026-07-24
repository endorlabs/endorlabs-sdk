"""Result types for the patch-fixable-findings report."""

from __future__ import annotations

from dataclasses import dataclass, field

from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.tabular import TabularExport


@dataclass
class PatchFixReportStats:
    """Aggregated statistics for a patch-fix report run."""

    namespace: str = ""
    project_count: int = 0
    finding_count: int = 0
    fixable_finding_count: int = 0
    package_group_count: int = 0


@dataclass
class PatchFixReportResult(WorkflowResult):
    """Patch-fix rollup plus optional per-finding detail rows."""

    stats: PatchFixReportStats = field(default_factory=PatchFixReportStats)
    table: TabularExport = field(default_factory=TabularExport)
    finding_detail: TabularExport = field(default_factory=TabularExport)
    signal_breakdown: dict[str, int] = field(default_factory=dict)

    @property
    def rows(self) -> list[dict[str, object]]:
        """Rollup rows (alias for ``table.rows``)."""
        return self.table.rows
