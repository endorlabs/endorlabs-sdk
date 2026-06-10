"""Intra-minor flattening and CVE-scoped remediation metrics on usage rows."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# CVE-2018-19362 micro-patch fix floors (Jackson #2186 / OSV).
_CVE_2018_19362_FIX_BY_MINOR: dict[tuple[int, int], tuple[int, ...]] = {
    (2, 6): (2, 6, 7, 3),
    (2, 7): (2, 7, 9, 5),
    (2, 8): (2, 8, 11, 3),
    (2, 9): (2, 9, 8, 0),
}


def parse_version_quad(version: str) -> tuple[int, int, int, int]:
    """Parse ``major.minor.patch.micro`` from a resolved version string."""
    base = version.split("-endor", maxsplit=1)[0]
    base = re.sub(r"-rc\d+$", "", base)
    base = re.sub(r"\.pr\d+$", "", base)
    nums: list[int] = []
    for part in base.split("."):
        match = re.match(r"(\d+)", part)
        if match:
            nums.append(int(match.group(1)))
    while len(nums) < 4:
        nums.append(0)
    return (nums[0], nums[1], nums[2], nums[3])


def minor_key(version: str) -> str:
    """Return ``major.minor`` key for grouping patch variants."""
    major, minor, _, _ = parse_version_quad(version)
    return f"{major}.{minor}"


def _version_sort_key(version: str) -> tuple[int, int, int, int, str]:
    return (*parse_version_quad(version), version)


def flatten_intra_minor_usage(
    version_counts: list[tuple[str, int]],
) -> list[tuple[str, int]]:
    """Collapse patch variants to the latest in-use patch per minor line."""
    by_minor: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for version, count in version_counts:
        by_minor[minor_key(version)].append((version, count))
    flattened: list[tuple[str, int]] = []
    for items in by_minor.values():
        best_version = max(items, key=lambda item: _version_sort_key(item[0]))[0]
        flattened.append((best_version, sum(count for _, count in items)))
    return sorted(flattened, key=lambda item: _version_sort_key(item[0]))


def cve_2018_19362_vulnerable(version: str) -> bool:
    """Return whether *version* is below the CVE-2018-19362 fix floor."""
    quad = parse_version_quad(version)
    line = (quad[0], quad[1])
    if line >= (2, 10):
        return False
    fix = _CVE_2018_19362_FIX_BY_MINOR.get(line)
    if fix is None:
        return True
    return quad[: len(fix)] < fix


def cve_2018_19362_fix_target(version: str) -> str:
    """Return the patched coordinate target for *version* on its minor line."""
    line = minor_key(version)
    if line >= "2.10":
        return version.split("-endor", maxsplit=1)[0]
    return {
        "2.6": "2.6.7.3",
        "2.7": "2.7.9.5",
        "2.8": "2.8.11.3",
        "2.9": "2.9.8",
    }.get(line, "2.9.8")


_CVE_POLICIES: dict[str, tuple[Callable[[str], bool], Callable[[str], str]]] = {
    "CVE-2018-19362": (cve_2018_19362_vulnerable, cve_2018_19362_fix_target),
}


def resolve_cve_policy(
    cve_id: str,
) -> tuple[Callable[[str], bool], Callable[[str], str]]:
    """Return ``(is_vulnerable, fix_target)`` callables for a supported CVE id."""
    key = cve_id.strip().upper()
    if key not in _CVE_POLICIES:
        supported = ", ".join(sorted(_CVE_POLICIES))
        raise ValueError(f"Unsupported CVE id {cve_id!r}; supported: {supported}")
    return _CVE_POLICIES[key]


@dataclass
class RemediationPhaseStats:
    """Metrics for one usage snapshot (as-is or flattened)."""

    label: str
    version_cardinality: int = 0
    dependency_instances: int = 0
    vulnerable_distinct_versions: int = 0
    vulnerable_instances: int = 0
    upgrade_paths_to_fix: int = 0
    already_patched_distinct_versions: int = 0
    already_patched_instances: int = 0


@dataclass
class RemediationComparisonResult:
    """Before/after intra-minor flattening for a CVE fix policy."""

    cve_id: str
    package_name: str = ""
    as_is: RemediationPhaseStats = field(default_factory=RemediationPhaseStats)
    flattened: RemediationPhaseStats = field(default_factory=RemediationPhaseStats)

    def to_dict(self) -> dict[str, Any]:
        """Serialize comparison metrics for JSON export."""

        def _phase(stats: RemediationPhaseStats) -> dict[str, int]:
            return {
                "version_cardinality": stats.version_cardinality,
                "dependency_instances": stats.dependency_instances,
                "vulnerable_distinct_versions": stats.vulnerable_distinct_versions,
                "vulnerable_instances": stats.vulnerable_instances,
                "upgrade_paths_to_fix": stats.upgrade_paths_to_fix,
                "already_patched_distinct_versions": (
                    stats.already_patched_distinct_versions
                ),
                "already_patched_instances": stats.already_patched_instances,
            }

        return {
            "cve_id": self.cve_id,
            "package_name": self.package_name,
            "as_is": _phase(self.as_is),
            "flattened": _phase(self.flattened),
            "delta": {
                "version_cardinality": (
                    self.as_is.version_cardinality - self.flattened.version_cardinality
                ),
                "upgrade_paths_to_fix": (
                    self.as_is.upgrade_paths_to_fix
                    - self.flattened.upgrade_paths_to_fix
                ),
            },
        }


def usage_rows_to_version_counts(
    usage_rows: list[dict[str, Any]],
) -> list[tuple[str, int]]:
    """Aggregate usage rows to ``(package_version, usage_count)`` pairs."""
    totals: dict[str, int] = defaultdict(int)
    for row in usage_rows:
        version = str(row.get("package_version") or "")
        totals[version] += int(row.get("usage_count") or 0)
    return sorted(totals.items(), key=lambda item: _version_sort_key(item[0]))


def summarize_remediation_phase(
    label: str,
    version_counts: list[tuple[str, int]],
    *,
    is_vulnerable: Callable[[str], bool],
    fix_target: Callable[[str], str],
) -> RemediationPhaseStats:
    """Compute remediation metrics for one usage snapshot."""
    vulnerable = [
        (version, count) for version, count in version_counts if is_vulnerable(version)
    ]
    upgrade_paths = {(version, fix_target(version)) for version, _ in vulnerable}
    total_instances = sum(count for _, count in version_counts)
    vulnerable_instances = sum(count for _, count in vulnerable)
    return RemediationPhaseStats(
        label=label,
        version_cardinality=len(version_counts),
        dependency_instances=total_instances,
        vulnerable_distinct_versions=len(vulnerable),
        vulnerable_instances=vulnerable_instances,
        upgrade_paths_to_fix=len(upgrade_paths),
        already_patched_distinct_versions=len(version_counts) - len(vulnerable),
        already_patched_instances=total_instances - vulnerable_instances,
    )


def analyze_intra_minor_remediation(
    usage_rows: list[dict[str, Any]],
    *,
    cve_id: str,
    package_name: str = "",
) -> RemediationComparisonResult:
    """Compare as-is vs intra-minor-flattened upgrade burden for ``cve_id``."""
    is_vulnerable, fix_target = resolve_cve_policy(cve_id)
    version_counts = usage_rows_to_version_counts(usage_rows)
    flattened_counts = flatten_intra_minor_usage(version_counts)
    return RemediationComparisonResult(
        cve_id=cve_id.strip().upper(),
        package_name=package_name,
        as_is=summarize_remediation_phase(
            "as_is",
            version_counts,
            is_vulnerable=is_vulnerable,
            fix_target=fix_target,
        ),
        flattened=summarize_remediation_phase(
            "flattened",
            flattened_counts,
            is_vulnerable=is_vulnerable,
            fix_target=fix_target,
        ),
    )
