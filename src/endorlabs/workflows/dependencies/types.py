"""Datatypes for dependency listing and visibility workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..common import WorkflowResult


def _empty_str_int_map() -> dict[str, int]:
    return {}


def _empty_dependency_rows() -> list[dict[str, Any]]:
    return []


@dataclass
class DependencyStats:
    """Aggregated statistics about dependencies."""

    total: int = 0
    by_namespace: dict[str, int] = field(default_factory=_empty_str_int_map)
    by_ecosystem: dict[str, int] = field(default_factory=_empty_str_int_map)
    by_scope: dict[str, int] = field(default_factory=_empty_str_int_map)
    by_reachability: dict[str, int] = field(default_factory=_empty_str_int_map)
    unique_packages: int = 0
    unique_importers: int = 0


@dataclass
class DependencyReport(WorkflowResult):
    """Result of listing project dependencies."""

    stats: DependencyStats = field(default_factory=DependencyStats)
    dependencies: list[dict[str, Any]] = field(default_factory=_empty_dependency_rows)


@dataclass
class VisibilityStats:
    """Aggregated visibility statistics."""

    total: int = 0
    public: int = 0
    private: int = 0
    unknown: int = 0
    by_ecosystem: dict[str, int] = field(default_factory=_empty_str_int_map)


@dataclass
class VisibilityReport(WorkflowResult):
    """Result of checking dependency visibility."""

    stats: VisibilityStats = field(default_factory=VisibilityStats)
