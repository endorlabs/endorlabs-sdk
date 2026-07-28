"""Scratch baseline parity checks for executive report packets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ONBOARDING_TOLERANCE_PCT = 1.0
SPRAWL_TOLERANCE_PCT = 2.0
THROUGHPUT_TOLERANCE_PCT = 5.0
BURNDOWN_EXACT_METRICS = frozenset({"burndown.gapEnd.all/all/all"})


@dataclass(frozen=True)
class MetricDelta:
    """One compared metric row."""

    metric: str
    new: int | float | None
    prior: int | float | None
    delta_pct: float | None
    within_tolerance: bool


def _pct_delta(new: float, prior: float) -> float:
    if prior == 0:
        return 0.0 if new == 0 else 100.0
    return abs(new - prior) / abs(prior) * 100.0


def _check(
    name: str,
    new: Any,
    prior: Any,
    *,
    tolerance_pct: float,
    exact: bool = False,
) -> MetricDelta:
    try:
        nf = float(new) if new is not None else None
        pf = float(prior) if prior is not None else None
    except (TypeError, ValueError):
        nf = pf = None
    delta = _pct_delta(nf, pf) if nf is not None and pf is not None else None
    if nf is None or pf is None:
        ok = new == prior
    elif exact:
        ok = nf == pf
    else:
        ok = delta is not None and delta <= tolerance_pct
    return MetricDelta(
        metric=name,
        new=new,
        prior=prior,
        delta_pct=delta,
        within_tolerance=ok,
    )


def compare_onboarding(
    onboarding: dict[str, Any],
    baseline_adoption: dict[str, Any],
) -> list[MetricDelta]:
    """Map scratch adoption JSON to packet onboarding metrics."""
    rows = [
        (
            "onboarding.allRegistrations",
            onboarding.get("allRegistrations"),
            baseline_adoption.get("raw_count"),
        ),
        (
            "onboarding.distinctRepositories",
            onboarding.get("distinctRepositories"),
            baseline_adoption.get("unique_by_name"),
        ),
        (
            "onboarding.duplicateRegistrations",
            onboarding.get("duplicateRegistrations"),
            baseline_adoption.get("duplicate_extra"),
        ),
    ]
    return [_check(n, a, b, tolerance_pct=ONBOARDING_TOLERANCE_PCT) for n, a, b in rows]


def compare_sprawl(
    version_sprawl: dict[str, Any],
    baseline_vc: dict[str, Any],
) -> list[MetricDelta]:
    """Map scratch version-cardinality cube to packet sprawl cell."""
    new_cell = ((version_sprawl.get("estate") or {}).get("all") or {}).get("all") or {}
    old_root = (baseline_vc.get("estate") or {}).get("all") or {}
    old_cell = old_root.get("all") if "packages" not in old_root else old_root
    rows = [
        ("sprawl.packages", new_cell.get("p"), old_cell.get("packages")),
        ("sprawl.versions", new_cell.get("v"), old_cell.get("versions")),
        ("sprawl.max", new_cell.get("max"), old_cell.get("max")),
    ]
    return [_check(n, a, b, tolerance_pct=SPRAWL_TOLERANCE_PCT) for n, a, b in rows]


def compare_findings_burndown(
    findings: dict[str, Any],
    baseline_fb: dict[str, Any],
    *,
    tag_catalog_count: int,
) -> list[MetricDelta]:
    """Map scratch burndown cube to packet findings burndown."""
    new_gap = (
        findings.get("seriesFilters", {})
        .get("perPath", {})
        .get("all", {})
        .get("all", {})
        .get("all", {})
        .get("gapEnd")
    )
    old_gap = (
        baseline_fb.get("seriesFilters", {})
        .get("perPath", {})
        .get("all", {})
        .get("all", {})
        .get("all", {})
        .get("gapEnd")
    )
    new_main = (
        findings.get("throughput", {})
        .get("perPath", {})
        .get("all", {})
        .get("mainScans91d")
    )
    old_main = (
        baseline_fb.get("throughput", {})
        .get("perPath", {})
        .get("all", {})
        .get("mainScans91d")
    )
    new_ci = (
        findings.get("throughput", {})
        .get("perPath", {})
        .get("all", {})
        .get("ciRunScans21d")
    )
    old_ci = (
        baseline_fb.get("throughput", {})
        .get("perPath", {})
        .get("all", {})
        .get("ciRunScans21d")
    )
    prior_tags = len(baseline_fb.get("tagOptions") or []) or len(
        baseline_fb.get("tagSeries", {}).get("tags") or []
    )
    return [
        _check(
            "burndown.gapEnd.all/all/all",
            new_gap,
            old_gap,
            tolerance_pct=0,
            exact=True,
        ),
        _check(
            "throughput.mainScans91d",
            new_main,
            old_main,
            tolerance_pct=THROUGHPUT_TOLERANCE_PCT,
        ),
        _check(
            "throughput.ciRunScans21d",
            new_ci,
            old_ci,
            tolerance_pct=THROUGHPUT_TOLERANCE_PCT,
        ),
        _check(
            "tagCatalog.count",
            tag_catalog_count,
            prior_tags,
            tolerance_pct=SPRAWL_TOLERANCE_PCT,
        ),
    ]


@dataclass(frozen=True)
class ParityReport:
    """Aggregated parity result."""

    rows: list[MetricDelta]

    @property
    def ok(self) -> bool:
        return all(r.within_tolerance for r in self.rows)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "rows": [
                {
                    "metric": r.metric,
                    "new": r.new,
                    "prior": r.prior,
                    "delta_pct": r.delta_pct,
                    "within_tolerance": r.within_tolerance,
                }
                for r in self.rows
            ],
        }


def compare_packet_cube(
    cube: dict[str, Any],
    *,
    baseline_adoption: dict[str, Any],
    baseline_sprawl: dict[str, Any],
    baseline_burndown: dict[str, Any],
) -> ParityReport:
    """Compare a packet cube against scratch baseline JSON blobs."""
    reports = cube.get("reports") or {}
    rows: list[MetricDelta] = []
    rows.extend(compare_onboarding(reports.get("onboarding") or {}, baseline_adoption))
    rows.extend(compare_sprawl(reports.get("versionSprawl") or {}, baseline_sprawl))
    rows.extend(
        compare_findings_burndown(
            reports.get("findingsBurndown") or {},
            baseline_burndown,
            tag_catalog_count=len(cube.get("tagCatalog") or []),
        )
    )
    return ParityReport(rows=rows)
