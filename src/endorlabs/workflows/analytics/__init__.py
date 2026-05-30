"""Tenant analytics workflows (estate aggregates, tabular exports)."""

from __future__ import annotations

from .export_dependencies import (
    export_estate_dependencies,
    export_version_cardinality,
    export_version_cardinality_for_package_match,
)
from .remediation import RemediationComparisonResult, analyze_intra_minor_remediation
from .types import (
    EstateDependencyExportResult,
    EstateDependencyExportStats,
    VersionCardinalityResult,
    VersionCardinalityStats,
)

__all__ = [
    "EstateDependencyExportResult",
    "EstateDependencyExportStats",
    "RemediationComparisonResult",
    "VersionCardinalityResult",
    "VersionCardinalityStats",
    "analyze_intra_minor_remediation",
    "export_estate_dependencies",
    "export_version_cardinality",
    "export_version_cardinality_for_package_match",
]
