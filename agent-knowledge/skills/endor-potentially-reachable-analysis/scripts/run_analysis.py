#!/usr/bin/env python3
"""Main-context PRF vulnerability + PV resolution error analysis."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.filters import prd_vuln_filter, prf_vuln_filter, pv_main_context_filter
from endorlabs.workflows.findings.prf_analysis import (
    ECO_LABEL,
    ECOSYSTEMS,
    PRD_LIST_MASK,
    PRF_AGG_MASK,
    aggregate_prf_metrics,
    fetch_parent_package_versions,
    findings_by_parent,
    list_findings_tenant,
    parent_uuids_by_eco,
)

PRF_BASE = prf_vuln_filter()
PRD_BASE = prd_vuln_filter()
PV_MAIN = pv_main_context_filter()


def parse_best_match(item: dict[str, Any] | None) -> dict[str, str]:
    if not item:
        return {
            "matching_rule": "no best match",
            "explanation": "",
            "fixable_notes": "",
            "fixable": "",
        }
    analysis = item.get("error_analysis_best_match") or {}
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except json.JSONDecodeError:
            analysis = {}
    if not isinstance(analysis, dict):
        analysis = {}
    rule = (analysis.get("matching_rule") or "").strip()
    return {
        "matching_rule": rule or "no best match",
        "explanation": str(analysis.get("explanation") or ""),
        "fixable_notes": str(analysis.get("fixable_notes") or ""),
        "fixable": (
            ""
            if analysis.get("fixable") is None
            else str(analysis.get("fixable")).lower()
        ),
    }


def has_dep_resolution_errors(pv: dict[str, Any]) -> bool:
    errors = (pv.get("spec") or {}).get("resolution_errors") or {}
    return bool(errors.get("unresolved") or errors.get("resolved"))


def has_call_graph_errors(pv: dict[str, Any]) -> bool:
    errors = (pv.get("spec") or {}).get("resolution_errors") or {}
    call_graph = errors.get("call_graph")
    return isinstance(call_graph, dict) and bool(call_graph)


def has_precomputed_reachability(pv: dict[str, Any]) -> bool:
    return (pv.get("spec") or {}).get(
        "precomputed_call_graph_state"
    ) == "PRECOMPUTED_STATE_SUCCESS"


def match_key(match: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        match["matching_rule"],
        match["explanation"],
        match["fixable_notes"],
        match["fixable"],
    )


def breakdown_rows(
    buckets: dict[tuple[str, str, str, str], set[str]],
    *,
    prf_by_parent: Any,
    prd_by_parent: Any,
    pv_by_uuid: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, pv_uuids in buckets.items():
        rule, explanation, fixable_notes, fixable = key
        rows.append(
            {
                "count": len(pv_uuids),
                "matching_rule": rule,
                "explanation": explanation,
                "fixable_notes": fixable_notes,
                "fixable": fixable,
                "prf_vulnerabilities": sum(prf_by_parent[uuid] for uuid in pv_uuids),
                "prd_vulnerabilities": sum(prd_by_parent[uuid] for uuid in pv_uuids),
                "precomputed_reachability_pvs": sum(
                    1
                    for uuid in pv_uuids
                    if has_precomputed_reachability(pv_by_uuid[uuid])
                ),
            }
        )
    rows.sort(key=lambda row: (-row["count"], row["matching_rule"]))
    return rows


def analyze_pv_errors(
    pvs_by_eco: dict[str, list[dict[str, Any]]],
    *,
    prf_by_parent: Any,
    prd_by_parent: Any,
    pv_by_uuid: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for eco in ECOSYSTEMS:
        pvs = pvs_by_eco.get(eco, [])
        dep_buckets: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
        call_buckets: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)

        for pv in pvs:
            uuid = str(pv.get("uuid") or "")
            if not uuid:
                continue
            errors = (pv.get("spec") or {}).get("resolution_errors") or {}
            if has_dep_resolution_errors(pv):
                item = errors.get("unresolved") or errors.get("resolved")
                match = parse_best_match(item if isinstance(item, dict) else None)
                dep_buckets[match_key(match)].add(uuid)

            if has_call_graph_errors(pv):
                match = parse_best_match(errors.get("call_graph"))
                call_buckets[match_key(match)].add(uuid)

        dep_pvs = sum(len(uuids) for uuids in dep_buckets.values())
        call_pvs = sum(len(uuids) for uuids in call_buckets.values())
        out[ECO_LABEL[eco]] = {
            "dep_resolution_error_pvs": dep_pvs,
            "dep_resolution_breakdown": breakdown_rows(
                dep_buckets,
                prf_by_parent=prf_by_parent,
                prd_by_parent=prd_by_parent,
                pv_by_uuid=pv_by_uuid,
            ),
            "call_graph_pvs": call_pvs,
            "call_graph_breakdown": breakdown_rows(
                call_buckets,
                prf_by_parent=prf_by_parent,
                prd_by_parent=prd_by_parent,
                pv_by_uuid=pv_by_uuid,
            ),
        }
    return out


def run_analysis(
    tenant: str,
    out_path: Path,
    *,
    max_pages: int | None = None,
    max_workers: int = 12,
    max_project_pages: int | None = None,
) -> dict[str, Any]:
    client = endorlabs.Client(tenant=tenant, timeout=600.0)
    try:
        print("Discovering project shards...")
        shards = client.Query.Project.discover(
            tenant,
            traverse=True,
            max_pages=max_project_pages,
            exclude_sbom=True,
        ).project_shards()
        print(f"Project shards: {len(shards)}")

        print("Listing PRF findings (counts derived from listed rows)...")
        prf_findings = list_findings_tenant(
            client,
            tenant,
            PRF_BASE,
            mask=PRF_AGG_MASK,
            max_pages=max_pages,
            max_workers=max_workers,
            shards=shards,
        )
        print(f"Listed {len(prf_findings)} PRF findings")
        prf_counts, approx_counts, not_approx_counts, prd_vuln_counts = (
            aggregate_prf_metrics(prf_findings)
        )
        prf_by_parent = findings_by_parent(prf_findings)
        parent_uuids_by_eco_map = parent_uuids_by_eco(prf_findings)

        print("Listing PRD findings for parent vulnerability counts...")
        prd_findings = list_findings_tenant(
            client,
            tenant,
            PRD_BASE,
            mask=PRD_LIST_MASK,
            max_pages=max_pages,
            max_workers=max_workers,
            shards=shards,
        )
        print(f"Listed {len(prd_findings)} PRD findings")
        prd_by_parent = findings_by_parent(prd_findings)

        all_parent_uuids = {
            uuid for uuids in parent_uuids_by_eco_map.values() for uuid in uuids
        }
        print(f"Unique PRF parent PV UUIDs: {len(all_parent_uuids)}")

        print("Hydrating parent PackageVersions...")
        pv_by_uuid = fetch_parent_package_versions(
            client,
            tenant,
            prf_findings,
            all_parent_uuids,
            pv_filter=PV_MAIN,
        )

        missing_parent_pvs = len(all_parent_uuids) - len(pv_by_uuid)
        print(f"Resolved {len(pv_by_uuid)} parent PVs ({missing_parent_pvs} missing)")

        pvs_by_eco: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for eco in ECOSYSTEMS:
            for uuid in parent_uuids_by_eco_map.get(eco, set()):
                pv = pv_by_uuid.get(uuid)
                if pv is not None:
                    pvs_by_eco[eco].append(pv)

        summary_rows: list[dict[str, Any]] = []
        total_unique: set[str] = set()
        total_dep_error = 0
        total_call_graph_error = 0

        for eco in ECOSYSTEMS:
            unique_pvs = len(pvs_by_eco[eco])
            dep_error_pvs = sum(
                1 for pv in pvs_by_eco[eco] if has_dep_resolution_errors(pv)
            )
            call_graph_error_pvs = sum(
                1 for pv in pvs_by_eco[eco] if has_call_graph_errors(pv)
            )
            total_unique.update(
                parent_uuids_by_eco_map.get(eco, set()) & set(pv_by_uuid)
            )
            total_dep_error += dep_error_pvs
            total_call_graph_error += call_graph_error_pvs
            prf_total = prf_counts.get(eco, 0)
            summary_rows.append(
                {
                    "ecosystem": ECO_LABEL[eco],
                    "prfVulnerabilities": prf_total,
                    "prdVulnerabilities": prd_vuln_counts.get(eco, 0),
                    "approximatedVulns": approx_counts.get(eco, 0),
                    "notApproximatedVulns": not_approx_counts.get(eco, 0),
                    "pctApproximatedVulns": round(
                        100.0 * approx_counts.get(eco, 0) / prf_total
                        if prf_total
                        else 0.0,
                        2,
                    ),
                    "uniquePvs": unique_pvs,
                    "pvsWithDepResolutionErrors": dep_error_pvs,
                    "pctPvsWithDepResolutionErrors": round(
                        100.0 * dep_error_pvs / unique_pvs if unique_pvs else 0.0,
                        2,
                    ),
                    "pvsWithCallGraphErrors": call_graph_error_pvs,
                    "pctPvsWithCallGraphErrors": round(
                        100.0 * call_graph_error_pvs / unique_pvs
                        if unique_pvs
                        else 0.0,
                        2,
                    ),
                    "isTotal": False,
                }
            )

        total_prf = sum(row["prfVulnerabilities"] for row in summary_rows)
        total_prd = sum(row["prdVulnerabilities"] for row in summary_rows)
        total_approx = sum(row["approximatedVulns"] for row in summary_rows)
        total_not_approx = sum(row["notApproximatedVulns"] for row in summary_rows)
        total_unique_count = len(total_unique)
        summary_rows.append(
            {
                "ecosystem": "Total",
                "prfVulnerabilities": total_prf,
                "prdVulnerabilities": total_prd,
                "approximatedVulns": total_approx,
                "notApproximatedVulns": total_not_approx,
                "pctApproximatedVulns": round(
                    100.0 * total_approx / total_prf if total_prf else 0.0, 2
                ),
                "uniquePvs": total_unique_count,
                "pvsWithDepResolutionErrors": total_dep_error,
                "pctPvsWithDepResolutionErrors": round(
                    100.0 * total_dep_error / total_unique_count
                    if total_unique_count
                    else 0.0,
                    2,
                ),
                "pvsWithCallGraphErrors": total_call_graph_error,
                "pctPvsWithCallGraphErrors": round(
                    100.0 * total_call_graph_error / total_unique_count
                    if total_unique_count
                    else 0.0,
                    2,
                ),
                "isTotal": True,
            }
        )

        ecosystem_errors = analyze_pv_errors(
            pvs_by_eco,
            prf_by_parent=prf_by_parent,
            prd_by_parent=prd_by_parent,
            pv_by_uuid=pv_by_uuid,
        )

        for eco in ECOSYSTEMS:
            label = ECO_LABEL[eco]
            summary = next(row for row in summary_rows if row["ecosystem"] == label)
            errors = ecosystem_errors[label]
            assert (
                errors["dep_resolution_error_pvs"]
                == summary["pvsWithDepResolutionErrors"]
            )
            assert errors["call_graph_pvs"] == summary["pvsWithCallGraphErrors"]
            dep_sum = sum(row["count"] for row in errors["dep_resolution_breakdown"])
            call_sum = sum(row["count"] for row in errors["call_graph_breakdown"])
            assert dep_sum == errors["dep_resolution_error_pvs"]
            assert call_sum == errors["call_graph_pvs"]

        result = {
            "tenant": tenant,
            "missing_parent_pvs": missing_parent_pvs,
            "prf_findings_listed": len(prf_findings),
            "prd_findings_listed": len(prd_findings),
            "project_shards": len(shards),
            "summary_rows": summary_rows,
            "ecosystem_errors": ecosystem_errors,
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Wrote {out_path}")
        return result
    finally:
        client.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query PRF findings and PRF-parent PV resolution errors."
    )
    parser.add_argument(
        "tenant",
        help="Tenant root namespace (traverse includes child namespaces).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            ".endorlabs-context/workspace/sessions/agent/exports/prf-analysis"
        ),
        help=(
            "Directory for {tenant}-prf-analysis.json "
            "(default: .endorlabs-context/workspace/sessions/agent/exports/prf-analysis)."
        ),
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional cap on finding list pagination depth per project shard.",
    )
    parser.add_argument(
        "--max-project-pages",
        type=int,
        default=None,
        help="Optional cap on Project discovery pagination when building shards.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=12,
        help="Parallel workers for per-project finding lists.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_path = args.output_dir / f"{args.tenant}-prf-analysis.json"
    run_analysis(
        args.tenant,
        out_path,
        max_pages=args.max_pages,
        max_workers=args.max_workers,
        max_project_pages=args.max_project_pages,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
