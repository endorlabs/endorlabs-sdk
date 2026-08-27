"""Endor Patches executive report cube from Finding rows.

Builds the ``reports.patches`` packet slice: top families by Available
reach-weighted risk, per-version heat-map rows, patch units, and a Java
(Maven) Crit/High finding-count denominator for the impact calculator.

Risk uses mild Critical/High bases (population is already severity-scoped)
and a **tiered** reach ladder across function and dependency tags:

``RF > RD > PRF > PRD > unreachable/none``. Confirmed function-reachable is
the strongest boost; potentially-reachable is inconclusive (not "reachable");
confirmed dependency-reachable is a milder boost than RF. Bar / ``projects``
counts are distinct Project UUIDs — a weak proxy for consumer blast radius;
PackageVersion-level consumers are not in this Finding rollup.

Finding lists are required for canonical heat maps; prefer leaf
``Finding.count`` only for the Java denominator. Documented as expensive at
estate scale — pair with ``--patches-only`` for campaign batch runs.

Collection (filter / list / detail rows) lives in
``endorlabs.workflows.findings.patch_core``; this module owns narrative
aggregation and the Java denominator.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any

from endorlabs.filters import FINDING_CATEGORY_VULNERABILITY, MAIN_CONTEXT_CLAUSE
from endorlabs.workflows.dependencies.coordinates import parse_dep_name
from endorlabs.workflows.findings.patch_core import (
    FINDING_MASK,
    NOT_DISMISSED_CLAUSE,
    build_finding_filter,
    compute_signal_breakdown,
    discover_and_list,
    extract_patch_rows,
)
from endorlabs.workflows.findings.prf_analysis import list_findings_tenant

if TYPE_CHECKING:
    from endorlabs import Client
    from endorlabs.tools.list_sharding import ProjectShard

# Population is already Critical/High — keep severity spread mild.
CRIT_W = 2.0
HIGH_W = 1.0
# Reach ladder (strongest evidence wins). Do not treat PRF/PRD as "reachable".
RF_MULT = 1.5
RD_MULT = 1.25
PRF_MULT = 1.0
PRD_MULT = 1.0
UNREACH_MULT = 0.75
TOP_N_FAMILIES = 5

_REACH_COUNT_KEYS = (
    "reachable_function",
    "potentially_reachable_function",
    "unreachable_function",
    "reachable_dependency",
    "potentially_reachable_dependency",
    "unreachable_dependency",
)

SEVERITIES = ("CRITICAL", "HIGH")

JAVA_DENOM_FILTER = (
    f"{MAIN_CONTEXT_CLAUSE} and "
    f"{NOT_DISMISSED_CLAUSE} and "
    "spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY] and "
    "(spec.level==FINDING_LEVEL_CRITICAL or spec.level==FINDING_LEVEL_HIGH) and "
    "spec.ecosystem == ECOSYSTEM_MAVEN"
)

IMPACT_DENOM_LABEL = "Fixable findings (Endor Patch units in view — any reachability)"
JAVA_DENOM_LABEL = "Java (Maven) Critical/High vulnerability findings (estate)"


def _family(package_name: str) -> str:
    fam, _ver = parse_dep_name(package_name or "")
    return fam or package_name


def _version(row: dict[str, Any]) -> str:
    cur = str(row.get("current_version") or "").strip()
    if cur:
        return cur
    _fam, embedded = parse_dep_name(str(row.get("package_name") or ""))
    return embedded or ""


def _truthy(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    return str(val or "").strip().lower() in {"1", "true", "yes", "y"}


def _sev_base(severity: str) -> float:
    sev = (severity or "").upper()
    if sev == "CRITICAL":
        return CRIT_W
    if sev == "HIGH":
        return HIGH_W
    return 0.0


def _reach_lane(row: dict[str, Any]) -> str:
    """Return strongest reach lane for risk (mutually exclusive priority).

    Order: ``rf`` > ``rd`` > ``prf`` > ``prd`` > ``uf`` > ``ud`` > ``none``.
    """
    if _truthy(row.get("reachable_function")):
        return "rf"
    if _truthy(row.get("reachable_dependency")):
        return "rd"
    if _truthy(row.get("potentially_reachable_function")):
        return "prf"
    if _truthy(row.get("potentially_reachable_dependency")):
        return "prd"
    if _truthy(row.get("unreachable_function")):
        return "uf"
    if _truthy(row.get("unreachable_dependency")):
        return "ud"
    return "none"


def _reach_mult(row: dict[str, Any]) -> float:
    lane = _reach_lane(row)
    if lane == "rf":
        return RF_MULT
    if lane == "rd":
        return RD_MULT
    if lane == "prf":
        return PRF_MULT
    if lane == "prd":
        return PRD_MULT
    return UNREACH_MULT


def _finding_risk(row: dict[str, Any]) -> float:
    return _sev_base(str(row.get("severity") or "")) * _reach_mult(row)


def _risk_weights_payload() -> dict[str, float]:
    return {
        "critical": CRIT_W,
        "high": HIGH_W,
        "reachable_function": RF_MULT,
        "reachable_dependency": RD_MULT,
        "potentially_reachable_function": PRF_MULT,
        "potentially_reachable_dependency": PRD_MULT,
        # Compat aliases for older HTML cubes.
        "potentially_reachable": PRF_MULT,
        "unreachable": UNREACH_MULT,
        "unreachable_function": UNREACH_MULT,
        "unreachable_dependency": UNREACH_MULT,
    }


def _empty_reach_counts() -> dict[str, int]:
    return {key: 0 for key in _REACH_COUNT_KEYS}


def _bump_reach_counts(counts: dict[str, int], row: dict[str, Any]) -> None:
    for key in _REACH_COUNT_KEYS:
        if _truthy(row.get(key)):
            counts[key] += 1


def _build_families(
    detail_rows: list[dict[str, Any]],
    *,
    top_n: int = TOP_N_FAMILIES,
) -> list[dict[str, Any]]:
    """Top families by Available reach-weighted risk."""
    fam_ver: dict[str, dict[str, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(
            lambda: {
                "available_uuids": set(),
                "to_request_uuids": set(),
                "avail_crit": 0,
                "avail_high": 0,
                "req_crit": 0,
                "req_high": 0,
                "avail_risk": 0.0,
                "req_risk": 0.0,
                "avail_reach": _empty_reach_counts(),
                "req_reach": _empty_reach_counts(),
                "projects": set(),
            }
        )
    )
    for row in detail_rows:
        status = str(row.get("patch_status") or "")
        if status not in ("available", "to_request_inferred"):
            continue
        fam = _family(str(row.get("package_name") or ""))
        ver = _version(row)
        if not fam:
            continue
        b = fam_ver[fam][ver or "(unknown)"]
        fid = str(row.get("finding_uuid") or "")
        sev = str(row.get("severity") or "").upper()
        weight = _finding_risk(row)
        if status == "available":
            if fid and fid not in b["available_uuids"]:
                b["available_uuids"].add(fid)
                b["avail_risk"] += weight
                _bump_reach_counts(b["avail_reach"], row)
                if sev == "CRITICAL":
                    b["avail_crit"] += 1
                elif sev == "HIGH":
                    b["avail_high"] += 1
        else:
            if fid and fid not in b["to_request_uuids"]:
                b["to_request_uuids"].add(fid)
                b["req_risk"] += weight
                _bump_reach_counts(b["req_reach"], row)
                if sev == "CRITICAL":
                    b["req_crit"] += 1
                elif sev == "HIGH":
                    b["req_high"] += 1
        proj = str(row.get("project_uuid") or "")
        if proj:
            b["projects"].add(proj)

    ranked: list[tuple[str, float, int, int]] = []
    for fam, versions in fam_ver.items():
        avail_risk = sum(float(v["avail_risk"]) for v in versions.values())
        ac = sum(int(v["avail_crit"]) for v in versions.values())
        ah = sum(int(v["avail_high"]) for v in versions.values())
        if ac + ah <= 0:
            continue
        ranked.append(
            (
                fam,
                avail_risk,
                ac + ah,
                sum(len(v["projects"]) for v in versions.values()),
            )
        )
    ranked.sort(key=lambda t: (-t[1], -t[2], -t[3], t[0]))
    top_fams = [t[0] for t in ranked[:top_n]]

    families: list[dict[str, Any]] = []
    for fam in top_fams:
        versions = fam_ver[fam]
        ver_rows: list[dict[str, Any]] = []
        total_avail_crit = total_avail_high = 0
        total_req_crit = total_req_high = 0
        total_avail_risk = 0.0
        all_projects: set[str] = set()
        for ver, b in versions.items():
            avail_n = len(b["available_uuids"])
            req_n = len(b["to_request_uuids"])
            if avail_n == 0 and req_n == 0:
                continue
            ac, ah = int(b["avail_crit"]), int(b["avail_high"])
            rc, rh = int(b["req_crit"]), int(b["req_high"])
            avail_risk = float(b["avail_risk"])
            req_risk = float(b["req_risk"])
            total_avail_crit += ac
            total_avail_high += ah
            total_req_crit += rc
            total_req_high += rh
            total_avail_risk += avail_risk
            all_projects |= b["projects"]
            reach_totals = {
                key: int(b["avail_reach"][key]) + int(b["req_reach"][key])
                for key in _REACH_COUNT_KEYS
            }
            rf_n = reach_totals["reachable_function"]
            ver_rows.append(
                {
                    "version": ver,
                    "available": avail_n,
                    "to_request": req_n,
                    "findings": avail_n + req_n,
                    "critical": ac + rc,
                    "high": ah + rh,
                    "avail_critical": ac,
                    "avail_high": ah,
                    "req_critical": rc,
                    "req_high": rh,
                    **reach_totals,
                    # Compat: RF-only alias; PRF count under potentially_reachable.
                    "reachable": rf_n,
                    "potentially_reachable": reach_totals[
                        "potentially_reachable_function"
                    ],
                    "unreachable": (
                        reach_totals["unreachable_function"]
                        + reach_totals["unreachable_dependency"]
                    ),
                    "projects": len(b["projects"]),
                    "risk": avail_risk + req_risk,
                    "risk_available": avail_risk,
                }
            )
        available_findings = total_avail_crit + total_avail_high
        to_request_findings = total_req_crit + total_req_high
        families.append(
            {
                "family": fam,
                # Total findings in the heat map (Available + To Request).
                "findings": available_findings + to_request_findings,
                "available_findings": available_findings,
                "to_request_findings": to_request_findings,
                # Severity badges remain Available-scoped (ranking is Available risk).
                "critical": total_avail_crit,
                "high": total_avail_high,
                "projects": len(all_projects),
                "versions": len(ver_rows),
                "risk": total_avail_risk,
                "version_rows": sorted(
                    ver_rows, key=lambda r: (-r["risk"], -r["projects"], r["version"])
                ),
            }
        )
    return families


def _patch_units(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for fam in families:
        for vr in fam.get("version_rows") or []:
            avail = int(vr.get("available") or 0)
            to_req = int(vr.get("to_request") or 0)
            if avail <= 0 and to_req <= 0:
                continue
            ac = int(vr.get("avail_critical") or 0)
            ah = int(vr.get("avail_high") or 0)
            rc = int(vr.get("req_critical") or 0)
            rh = int(vr.get("req_high") or 0)
            units.append(
                {
                    "family": fam["family"],
                    "version": vr["version"],
                    "package_version": f"{fam['family']}@{vr['version']}",
                    "available": avail,
                    "to_request": to_req,
                    "findings": avail + to_req,
                    "avail_critical": ac,
                    "avail_high": ah,
                    "req_critical": rc,
                    "req_high": rh,
                    "critical": ac + rc,
                    "high": ah + rh,
                    "projects": int(vr.get("projects") or 0),
                    "risk": float(vr.get("risk") or 0),
                    "risk_available": float(vr.get("risk_available") or 0),
                    "reachable_function": int(vr.get("reachable_function") or 0),
                    "potentially_reachable_function": int(
                        vr.get("potentially_reachable_function")
                        or vr.get("potentially_reachable")
                        or 0
                    ),
                    "unreachable_function": int(vr.get("unreachable_function") or 0),
                    "reachable_dependency": int(vr.get("reachable_dependency") or 0),
                    "potentially_reachable_dependency": int(
                        vr.get("potentially_reachable_dependency") or 0
                    ),
                    "unreachable_dependency": int(
                        vr.get("unreachable_dependency") or 0
                    ),
                    "potentially_reachable": int(
                        vr.get("potentially_reachable_function")
                        or vr.get("potentially_reachable")
                        or 0
                    ),
                    "unreachable": int(vr.get("unreachable") or 0),
                    "reachable": int(vr.get("reachable_function") or 0),
                }
            )
    units.sort(
        key=lambda u: (-u["risk"], -u["findings"], -u["projects"], u["package_version"])
    )
    return units


def count_java_maven_crit_high(
    client: Client,
    namespace: str,
    *,
    max_workers: int = 12,
    leaf_namespaces: Sequence[str] | None = None,
) -> tuple[int, int]:
    """Sum leaf ``Finding.count`` for Java Maven Crit/High vulns.

    When *leaf_namespaces* is provided (e.g. non-SBOM leaves from packet
    discover), skip ``Query.Project.discover`` rediscovery.

    Returns ``(count, leaf_namespace_count)``.
    """
    if leaf_namespaces is not None:
        leaves = [ns for ns in leaf_namespaces if ns] or [namespace]
    else:
        leaves = sorted(
            {
                s.namespace
                for s in client.Query.Project.discover(
                    namespace, traverse=True, exclude_sbom=True
                ).project_shards()
                if s.namespace
            }
        )
        if not leaves:
            leaves = [namespace]

    def one(ns: str) -> int:
        return int(
            client.Finding.count(namespace=ns, traverse=False, filter=JAVA_DENOM_FILTER)
        )

    total = 0
    workers = max(1, min(max_workers, len(leaves)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(one, ns) for ns in leaves]
        for fut in as_completed(futs):
            total += fut.result()
    return total, len(leaves)


def empty_patches_report() -> dict[str, Any]:
    """Empty ``reports.patches`` slice when the page is skipped."""
    return {
        "top_n_families": TOP_N_FAMILIES,
        "rollup_mode": "",
        "estate_available_findings": 0,
        "estate_impact_denominator": 0,
        "estate_java_findings": None,
        "denominator_label": IMPACT_DENOM_LABEL,
        "java_denominator_label": JAVA_DENOM_LABEL,
        "denominator_source": "",
        "risk_weights": _risk_weights_payload(),
        "signal_breakdown": {},
        "families": [],
        "patch_units": [],
        "patch_unit_count": 0,
    }


def collect_patches_report(
    client: Client,
    namespace: str,
    *,
    max_workers: int = 8,
    top_n_families: int = TOP_N_FAMILIES,
    include_java_denominator: bool = True,
    finding_categories: Sequence[str] = (FINDING_CATEGORY_VULNERABILITY,),
    severities: Sequence[str] | None = None,
    gate: str = "any",
    shards: Sequence[ProjectShard] | None = None,
    leaf_namespaces: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Pull patch-gated findings and build the patches cube slice.

    Defaults match the Endor Patches narrative: vulnerability findings at
    Critical/High with ``gate="any"`` and any reachability. The product
    Patches dashboard **Available** header is RF or PRF only — do not treat
    this slice as that header. Pass *finding_categories* / *severities* /
    *gate* to reuse the same collector for alternate presets.

    When *shards* is provided (e.g. from packet ``discover_projects``), skip
    rediscovery and list findings on those shards only. Pass
    *leaf_namespaces* (non-SBOM leaves) so the Java denom skips a second
    ``Query.Project.discover``.
    """
    sev = list(SEVERITIES if severities is None else severities)
    finding_filter = build_finding_filter(finding_categories, sev, gate=gate)
    if shards is not None:
        shard_list = list(shards)
        if not shard_list:
            return empty_patches_report()
        findings = list_findings_tenant(
            client,
            namespace,
            finding_filter,
            mask=FINDING_MASK,
            max_workers=max_workers,
            shards=shard_list,
        )
    else:
        shard_list, findings = discover_and_list(
            client,
            namespace,
            finding_filter,
            max_workers=max_workers,
        )

    if not shard_list:
        return empty_patches_report()

    signal_breakdown = compute_signal_breakdown(findings)
    detail = extract_patch_rows(findings)
    families = _build_families(detail, top_n=top_n_families)
    units = _patch_units(families)
    available_uuids = {
        str(r.get("finding_uuid") or "")
        for r in detail
        if r.get("patch_status") == "available" and r.get("finding_uuid")
    }
    java_count: int | None = None
    if include_java_denominator:
        java_leaves = (
            list(leaf_namespaces)
            if leaf_namespaces is not None
            else sorted({s.namespace for s in shard_list if s.namespace})
        )
        java_count, _leaves = count_java_maven_crit_high(
            client,
            namespace,
            max_workers=max_workers,
            leaf_namespaces=java_leaves or None,
        )

    endor_patch_n = int(signal_breakdown.get("endor_patch_available_count") or 0)
    # Donut denom is computed in HTML from patch_units in the active view
    # (Fixable findings, any reachability — not the product RF|PRF header).
    return {
        "top_n_families": top_n_families,
        "rollup_mode": "target_dependency",
        "estate_available_findings": len(available_uuids),
        "estate_impact_denominator": endor_patch_n,
        "estate_java_findings": java_count,
        "denominator_label": IMPACT_DENOM_LABEL,
        "java_denominator_label": JAVA_DENOM_LABEL,
        "denominator_source": "fixable_pool_in_view",
        "risk_weights": _risk_weights_payload(),
        "signal_breakdown": signal_breakdown,
        "families": families,
        "patch_units": units,
        "patch_unit_count": len(units),
        "project_count": len(shard_list),
        "finding_count": len(findings),
        "detail_row_count": len(detail),
    }
