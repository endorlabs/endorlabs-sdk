"""Pluggable finding-centric risk scoring for estate analytics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from endorlabs.workflows.dependencies.coordinates import parse_dep_name

FINDING_LEVEL_CRITICAL = "FINDING_LEVEL_CRITICAL"
FINDING_LEVEL_HIGH = "FINDING_LEVEL_HIGH"

DEFAULT_CRITICAL_WEIGHT = 4.0
DEFAULT_HIGH_WEIGHT = 2.0
DEFAULT_MISSING_EPSS_PRIOR = 0.05


@dataclass
class PackageRiskSummary:
    """Aggregated risk for one dependency package coordinate."""

    package_name: str
    risk_score: float = 0.0
    findings_critical: int = 0
    findings_high: int = 0
    findings_total: int = 0
    findings_unscored: int = 0


@dataclass
class VersionRiskSummary:
    """Aggregated risk for one package version."""

    package_name: str
    version: str
    risk_score: float = 0.0
    findings_critical: int = 0
    findings_high: int = 0
    findings_total: int = 0
    orphan: bool = False


class RiskScorer(Protocol):
    """Score individual findings and roll up package-level summaries."""

    name: str

    def score_finding(self, finding: dict[str, Any]) -> float:
        """Return a numeric contribution for one normalized finding record."""
        ...

    def aggregate_packages(
        self, findings: list[dict[str, Any]]
    ) -> dict[str, PackageRiskSummary]:
        """Roll up findings by package coordinate."""
        ...


def normalize_level(raw: Any) -> str:
    if hasattr(raw, "value"):
        return str(raw.value)
    return str(raw or "")


def finding_package_key(spec: dict[str, Any]) -> str | None:
    """Resolve grouping key for a finding's dependency coordinate."""
    qualified = spec.get("target_dependency_package_name")
    if qualified:
        return str(qualified)
    name = spec.get("target_dependency_name")
    if name:
        return str(name)
    return None


def package_family_name(package_key: str) -> str:
    """Strip an embedded ``@version`` suffix for DependencyMetadata lookup."""
    family, _embedded = parse_dep_name(package_key)
    return family or package_key


def dm_package_name_for_key(package_key: str) -> str:
    """Package name as stored on ``spec.dependency_data.package_name``."""
    return package_family_name(package_key)


def finding_version(spec: dict[str, Any]) -> str:
    raw = spec.get("target_dependency_version")
    return str(raw or "")


def finding_spec_dict(finding: Any) -> dict[str, Any]:
    if isinstance(finding, dict):
        spec = finding.get("spec")
        return spec if isinstance(spec, dict) else {}
    spec = getattr(finding, "spec", None)
    if spec is None:
        return {}
    if hasattr(spec, "model_dump"):
        dumped = spec.model_dump(mode="json", warnings=False)
        return dumped if isinstance(dumped, dict) else {}
    return {}


def normalize_finding_record(finding: Any) -> dict[str, Any]:
    """Return a dict with ``spec`` suitable for scoring and joins."""
    if isinstance(finding, dict):
        spec = finding.get("spec")
        if isinstance(spec, dict):
            return {"spec": spec}
        return {"spec": finding_spec_dict(finding)}
    return {"spec": finding_spec_dict(finding)}


@dataclass
class CriticalHighCountScorer:
    """Weight Critical and High severities (default estate ranking)."""

    name: str = "critical_high_count"
    critical_weight: float = DEFAULT_CRITICAL_WEIGHT
    high_weight: float = DEFAULT_HIGH_WEIGHT

    def score_finding(self, finding: dict[str, Any]) -> float:
        spec = finding.get("spec") or {}
        level = normalize_level(spec.get("level"))
        if level == FINDING_LEVEL_CRITICAL:
            return self.critical_weight
        if level == FINDING_LEVEL_HIGH:
            return self.high_weight
        return 0.0

    def aggregate_packages(
        self, findings: list[dict[str, Any]]
    ) -> dict[str, PackageRiskSummary]:
        summaries: dict[str, PackageRiskSummary] = {}
        for finding in findings:
            spec = finding.get("spec") or {}
            level = normalize_level(spec.get("level"))
            if level not in (FINDING_LEVEL_CRITICAL, FINDING_LEVEL_HIGH):
                continue
            package_name = finding_package_key(spec)
            if not package_name:
                continue
            summary = summaries.get(package_name)
            if summary is None:
                summary = PackageRiskSummary(package_name=package_name)
                summaries[package_name] = summary
            summary.findings_total += 1
            if level == FINDING_LEVEL_CRITICAL:
                summary.findings_critical += 1
            elif level == FINDING_LEVEL_HIGH:
                summary.findings_high += 1
            summary.risk_score += self.score_finding(finding)
        return summaries


@dataclass
class EpssWeightedScorer:
    """Multiply base severity weights by EPSS score when present.

    Missing EPSS uses ``missing_epss_prior`` (default 0.05). Population median
    EPSS is ~0.004; 0.05 is conservative so unscored findings do not rank above
    most scored CVEs while remaining visibly distinct from max exploitability.
    """

    name: str = "epss_weighted"
    critical_weight: float = DEFAULT_CRITICAL_WEIGHT
    high_weight: float = DEFAULT_HIGH_WEIGHT
    missing_epss_prior: float = DEFAULT_MISSING_EPSS_PRIOR

    def _epss_multiplier(self, spec: dict[str, Any]) -> tuple[float, bool]:
        """Return (multiplier, used_prior)."""
        epss_block = spec.get("epss_score")
        if not isinstance(epss_block, dict):
            return self.missing_epss_prior, True
        raw = epss_block.get("score")
        if raw is None:
            return self.missing_epss_prior, True
        return max(float(raw), 0.0), False

    def score_finding(self, finding: dict[str, Any]) -> float:
        spec = finding.get("spec") or {}
        level = normalize_level(spec.get("level"))
        base = 0.0
        if level == FINDING_LEVEL_CRITICAL:
            base = self.critical_weight
        elif level == FINDING_LEVEL_HIGH:
            base = self.high_weight
        if base <= 0:
            return 0.0
        multiplier, _ = self._epss_multiplier(spec)
        return base * multiplier

    def aggregate_packages(
        self, findings: list[dict[str, Any]]
    ) -> dict[str, PackageRiskSummary]:
        summaries: dict[str, PackageRiskSummary] = {}
        for finding in findings:
            spec = finding.get("spec") or {}
            package_name = finding_package_key(spec)
            if not package_name:
                continue
            summary = summaries.get(package_name)
            if summary is None:
                summary = PackageRiskSummary(package_name=package_name)
                summaries[package_name] = summary
            level = normalize_level(spec.get("level"))
            summary.findings_total += 1
            if level == FINDING_LEVEL_CRITICAL:
                summary.findings_critical += 1
            elif level == FINDING_LEVEL_HIGH:
                summary.findings_high += 1
            _, used_prior = self._epss_multiplier(spec)
            if used_prior:
                summary.findings_unscored += 1
            summary.risk_score += self.score_finding(finding)
        return summaries


@dataclass
class ReachabilityTagScorer:
    """Boost reachable dependency findings using ``spec.finding_tags``."""

    name: str = "reachability_tag"
    critical_weight: float = DEFAULT_CRITICAL_WEIGHT
    high_weight: float = DEFAULT_HIGH_WEIGHT
    reachable_multiplier: float = 1.5

    def _tags(self, spec: dict[str, Any]) -> list[str]:
        raw = spec.get("finding_tags") or []
        if isinstance(raw, str):
            return [raw]
        return [str(t) for t in raw]

    def score_finding(self, finding: dict[str, Any]) -> float:
        spec = finding.get("spec") or {}
        level = normalize_level(spec.get("level"))
        base = 0.0
        if level == FINDING_LEVEL_CRITICAL:
            base = self.critical_weight
        elif level == FINDING_LEVEL_HIGH:
            base = self.high_weight
        if base <= 0:
            return 0.0
        tags = self._tags(spec)
        if "FINDING_TAGS_REACHABLE_DEPENDENCY" in tags:
            return base * self.reachable_multiplier
        return base

    def aggregate_packages(
        self, findings: list[dict[str, Any]]
    ) -> dict[str, PackageRiskSummary]:
        summaries: dict[str, PackageRiskSummary] = {}
        for finding in findings:
            spec = finding.get("spec") or {}
            package_name = finding_package_key(spec)
            if not package_name:
                continue
            summary = summaries.get(package_name)
            if summary is None:
                summary = PackageRiskSummary(package_name=package_name)
                summaries[package_name] = summary
            level = normalize_level(spec.get("level"))
            summary.findings_total += 1
            if level == FINDING_LEVEL_CRITICAL:
                summary.findings_critical += 1
            elif level == FINDING_LEVEL_HIGH:
                summary.findings_high += 1
            summary.risk_score += self.score_finding(finding)
        return summaries


SCORER_REGISTRY: dict[str, RiskScorer] = {
    CriticalHighCountScorer.name: CriticalHighCountScorer(),
    EpssWeightedScorer.name: EpssWeightedScorer(),
    ReachabilityTagScorer.name: ReachabilityTagScorer(),
}


def resolve_scorer(name: str) -> RiskScorer:
    key = name.strip().lower()
    if key not in SCORER_REGISTRY:
        supported = ", ".join(sorted(SCORER_REGISTRY))
        msg = f"Unsupported scorer {name!r}; supported: {supported}"
        raise ValueError(msg)
    return SCORER_REGISTRY[key]


def rank_packages(
    summaries: dict[str, PackageRiskSummary],
) -> list[PackageRiskSummary]:
    """Sort packages by risk score, then finding count, then name."""
    return sorted(
        summaries.values(),
        key=lambda item: (
            -item.risk_score,
            -item.findings_total,
            item.package_name,
        ),
    )


def aggregate_findings_by_version(
    findings: list[dict[str, Any]],
    *,
    scorer: RiskScorer,
    package_name: str,
) -> dict[str, VersionRiskSummary]:
    """Roll up findings for one package keyed by dependency version."""
    by_version: dict[str, VersionRiskSummary] = {}
    for finding in findings:
        spec = finding.get("spec") or {}
        key = finding_package_key(spec)
        if key != package_name:
            continue
        version = finding_version(spec)
        summary = by_version.get(version)
        if summary is None:
            summary = VersionRiskSummary(package_name=package_name, version=version)
            by_version[version] = summary
        level = normalize_level(spec.get("level"))
        summary.findings_total += 1
        if level == FINDING_LEVEL_CRITICAL:
            summary.findings_critical += 1
        elif level == FINDING_LEVEL_HIGH:
            summary.findings_high += 1
        summary.risk_score += scorer.score_finding(finding)
    return by_version


def aggregate_families(
    findings: list[dict[str, Any]],
    scorer: RiskScorer,
) -> dict[str, PackageRiskSummary]:
    """Roll up findings by package family (strip embedded coordinate version)."""
    remapped: list[dict[str, Any]] = []
    for finding in findings:
        spec = dict(finding.get("spec") or {})
        key = finding_package_key(spec)
        if not key:
            continue
        remapped.append(
            {
                "spec": {
                    **spec,
                    "target_dependency_package_name": package_family_name(key),
                }
            }
        )
    return scorer.aggregate_packages(remapped)


def aggregate_family_findings_by_version(
    findings: list[dict[str, Any]],
    *,
    family_name: str,
    scorer: RiskScorer,
) -> dict[str, VersionRiskSummary]:
    """Roll up findings for one package family keyed by dependency version."""
    by_version: dict[str, VersionRiskSummary] = {}
    for finding in findings:
        spec = finding.get("spec") or {}
        key = finding_package_key(spec)
        if not key or package_family_name(key) != family_name:
            continue
        version = finding_version(spec)
        if not version:
            _family, embedded = parse_dep_name(key)
            version = embedded
        if not version:
            continue
        summary = by_version.get(version)
        if summary is None:
            summary = VersionRiskSummary(package_name=family_name, version=version)
            by_version[version] = summary
        level = normalize_level(spec.get("level"))
        summary.findings_total += 1
        if level == FINDING_LEVEL_CRITICAL:
            summary.findings_critical += 1
        elif level == FINDING_LEVEL_HIGH:
            summary.findings_high += 1
        summary.risk_score += scorer.score_finding(finding)
    return by_version


def join_version_usage_and_risk(
    usage_rows: list[dict[str, Any]],
    version_risk: dict[str, VersionRiskSummary],
    *,
    package_name: str,
    usage_package_name: str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Merge usage counts with per-version finding risk; return rows and warnings."""
    dm_name = usage_package_name or dm_package_name_for_key(package_name)
    warnings: list[str] = []
    usage_by_version: dict[str, int] = {}
    for row in usage_rows:
        if str(row.get("package_name")) != dm_name:
            continue
        version = str(row.get("package_version") or "")
        usage_by_version[version] = usage_by_version.get(version, 0) + int(
            row.get("usage_count") or 0
        )

    all_versions = set(usage_by_version) | set(version_risk)
    joined: list[dict[str, Any]] = []
    for version in sorted(all_versions, key=lambda v: (-usage_by_version.get(v, 0), v)):
        risk = version_risk.get(version)
        usage = usage_by_version.get(version, 0)
        if risk is None and usage > 0:
            joined.append(
                {
                    "package_name": package_name,
                    "version": version,
                    "usage_count": usage,
                    "findings_critical": 0,
                    "findings_high": 0,
                    "findings_total": 0,
                    "risk_score": 0.0,
                    "orphan": False,
                }
            )
            continue
        if risk is not None and usage == 0:
            warnings.append(
                f"{package_name} ({version}): findings without DependencyMetadata usage"
            )
            joined.append(
                {
                    "package_name": package_name,
                    "version": version,
                    "usage_count": 0,
                    "findings_critical": risk.findings_critical,
                    "findings_high": risk.findings_high,
                    "findings_total": risk.findings_total,
                    "risk_score": risk.risk_score,
                    "orphan": True,
                }
            )
            continue
        if risk is None:
            continue
        joined.append(
            {
                "package_name": package_name,
                "version": version,
                "usage_count": usage,
                "findings_critical": risk.findings_critical,
                "findings_high": risk.findings_high,
                "findings_total": risk.findings_total,
                "risk_score": risk.risk_score,
                "orphan": False,
            }
        )
    return joined, warnings
