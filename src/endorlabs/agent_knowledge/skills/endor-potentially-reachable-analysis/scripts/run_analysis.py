#!/usr/bin/env python3
"""Main-context PRF vulnerability + PV resolution error analysis."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import endorlabs

ECOSYSTEMS = ["NUGET", "NPM", "MAVEN", "PYPI"]
ECO_ENUM = {
    "NUGET": "ECOSYSTEM_NUGET",
    "NPM": "ECOSYSTEM_NPM",
    "MAVEN": "ECOSYSTEM_MAVEN",
    "PYPI": "ECOSYSTEM_PYPI",
}
ECO_LABEL = {
    "NUGET": "NuGet",
    "NPM": "NPM",
    "MAVEN": "Maven",
    "PYPI": "PyPI",
}
PRF_BASE = (
    "context.type==CONTEXT_TYPE_MAIN "
    "and spec.finding_categories contains FINDING_CATEGORY_VULNERABILITY "
    "and spec.finding_tags contains FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION"
)
PRD_BASE = (
    "context.type==CONTEXT_TYPE_MAIN "
    "and spec.finding_categories contains FINDING_CATEGORY_VULNERABILITY "
    "and spec.finding_tags contains FINDING_TAGS_POTENTIALLY_REACHABLE_DEPENDENCY"
)
PV_MAIN = "context.type==CONTEXT_TYPE_MAIN"
PV_BATCH = 50


def list_params(**kwargs: object) -> dict[str, str]:
    out: dict[str, str] = {
        "list_parameters.traverse": "true",
    }
    for key, value in kwargs.items():
        out[f"list_parameters.{key}"] = (
            str(value).lower() if isinstance(value, bool) else str(value)
        )
    return out


def count_findings(api: Any, tenant: str, filt: str) -> int:
    resp = api.get(
        f"v1/namespaces/{tenant}/findings",
        params=list_params(filter=filt, count=True),
    )
    resp.raise_for_status()
    return int(resp.json().get("count_response", {}).get("count", 0))


def list_findings(api: Any, tenant: str, filt: str) -> list[dict[str, Any]]:
    return list(
        api.get_all(
            f"v1/namespaces/{tenant}/findings",
            params=list_params(filter=filt, page_size=500),
        )
    )


def get_pvs_batch(api: Any, tenant: str, uuids: list[str]) -> list[dict[str, Any]]:
    if not uuids:
        return []
    quoted = ", ".join(f'"{uuid}"' for uuid in uuids)
    filt = f"{PV_MAIN} and uuid in [{quoted}]"
    return list(
        api.get_all(
            f"v1/namespaces/{tenant}/package-versions",
            params=list_params(filter=filt, page_size=100),
        )
    )


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
    return (
        (pv.get("spec") or {}).get("precomputed_call_graph_state")
        == "PRECOMPUTED_STATE_SUCCESS"
    )


def findings_by_parent(findings: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for finding in findings:
        parent_uuid = (finding.get("meta") or {}).get("parent_uuid")
        if parent_uuid:
            counts[str(parent_uuid)] += 1
    return counts


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
    prf_by_parent: Counter[str],
    prd_by_parent: Counter[str],
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
    prf_by_parent: Counter[str],
    prd_by_parent: Counter[str],
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


def run_analysis(tenant: str, out_path: Path) -> dict[str, Any]:
    client = endorlabs.Client(tenant=tenant, timeout=600.0)
    try:
        api = client._client
        assert api is not None

        parent_uuids_by_eco: dict[str, set[str]] = defaultdict(set)
        prf_counts: dict[str, int] = defaultdict(int)
        prd_vuln_counts: dict[str, int] = defaultdict(int)
        approx_counts: dict[str, int] = defaultdict(int)
        not_approx_counts: dict[str, int] = defaultdict(int)

        for eco in ECOSYSTEMS:
            eco_filter = f"{PRF_BASE} and spec.ecosystem=={ECO_ENUM[eco]}"
            prf_counts[eco] = count_findings(api, tenant, eco_filter)
            prd_vuln_counts[eco] = count_findings(
                api,
                tenant,
                f"{eco_filter} and spec.finding_tags contains FINDING_TAGS_POTENTIALLY_REACHABLE_DEPENDENCY",
            )
            approx_counts[eco] = count_findings(
                api, tenant, f"{eco_filter} and spec.approximation==true"
            )
            not_approx_counts[eco] = count_findings(
                api, tenant, f"{eco_filter} and spec.approximation==false"
            )

        print("Listing PRF findings for parent PV collection...")
        prf_findings = list_findings(api, tenant, PRF_BASE)
        print(f"Listed {len(prf_findings)} PRF findings")
        prf_by_parent = findings_by_parent(prf_findings)

        print("Listing PRD findings for parent vulnerability counts...")
        prd_findings = list_findings(api, tenant, PRD_BASE)
        print(f"Listed {len(prd_findings)} PRD findings")
        prd_by_parent = findings_by_parent(prd_findings)

        for finding in prf_findings:
            eco = (finding.get("spec") or {}).get("ecosystem", "")
            if eco not in ECO_ENUM.values():
                continue
            parent_uuid = (finding.get("meta") or {}).get("parent_uuid")
            if parent_uuid:
                for key, enum in ECO_ENUM.items():
                    if enum == eco:
                        parent_uuids_by_eco[key].add(parent_uuid)
                        break

        all_parent_uuids = sorted(
            {uuid for uuids in parent_uuids_by_eco.values() for uuid in uuids}
        )
        print(f"Unique PRF parent PV UUIDs: {len(all_parent_uuids)}")

        pv_by_uuid: dict[str, dict[str, Any]] = {}
        for idx in range(0, len(all_parent_uuids), PV_BATCH):
            batch = all_parent_uuids[idx : idx + PV_BATCH]
            for pv in get_pvs_batch(api, tenant, batch):
                uuid = pv.get("uuid")
                if uuid:
                    pv_by_uuid[str(uuid)] = pv

        missing_parent_pvs = len(all_parent_uuids) - len(pv_by_uuid)
        print(f"Resolved {len(pv_by_uuid)} parent PVs ({missing_parent_pvs} missing)")

        pvs_by_eco: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for eco in ECOSYSTEMS:
            for uuid in parent_uuids_by_eco[eco]:
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
            total_unique.update(parent_uuids_by_eco[eco] & set(pv_by_uuid))
            total_dep_error += dep_error_pvs
            total_call_graph_error += call_graph_error_pvs
            prf_total = prf_counts[eco]
            summary_rows.append(
                {
                    "ecosystem": ECO_LABEL[eco],
                    "prfVulnerabilities": prf_total,
                    "prdVulnerabilities": prd_vuln_counts[eco],
                    "approximatedVulns": approx_counts[eco],
                    "notApproximatedVulns": not_approx_counts[eco],
                    "pctApproximatedVulns": round(
                        100.0 * approx_counts[eco] / prf_total if prf_total else 0.0,
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
            assert errors["dep_resolution_error_pvs"] == summary[
                "pvsWithDepResolutionErrors"
            ]
            assert errors["call_graph_pvs"] == summary["pvsWithCallGraphErrors"]
            dep_sum = sum(row["count"] for row in errors["dep_resolution_breakdown"])
            call_sum = sum(row["count"] for row in errors["call_graph_breakdown"])
            assert dep_sum == errors["dep_resolution_error_pvs"]
            assert call_sum == errors["call_graph_pvs"]

        result = {
            "tenant": tenant,
            "missing_parent_pvs": missing_parent_pvs,
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_path = args.output_dir / f"{args.tenant}-prf-analysis.json"
    run_analysis(args.tenant, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
