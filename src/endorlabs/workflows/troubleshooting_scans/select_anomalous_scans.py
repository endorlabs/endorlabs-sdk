"""Select suspicious scan-result pairs from scan summary data."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .common import load_json, write_json


def anomaly_score(
    current: dict[str, Any],
    previous: dict[str, Any],
    min_delta_findings: int,
    min_delta_deps: int,
) -> tuple[int, list[str]]:
    """Score a candidate pair and return reasons."""
    score = 0
    reasons: list[str] = []

    if current.get("status") in {"STATUS_FAILURE", "STATUS_PARTIAL_SUCCESS"}:
        score += 2
        reasons.append(f"status={current.get('status')}")

    findings_current = sum(
        int(current.get(k, 0))
        for k in (
            "findings_critical",
            "findings_high",
            "findings_medium",
            "findings_low",
        )
    )
    findings_previous = sum(
        int(previous.get(k, 0))
        for k in (
            "findings_critical",
            "findings_high",
            "findings_medium",
            "findings_low",
        )
    )
    findings_delta = abs(findings_current - findings_previous)
    if findings_delta >= min_delta_findings:
        score += 2
        reasons.append(f"findings_delta={findings_delta}")

    deps_delta = abs(
        int(current.get("dependency_count_total", 0))
        - int(previous.get("dependency_count_total", 0))
    )
    if deps_delta >= min_delta_deps:
        score += 3
        reasons.append(f"dependency_count_total_delta={deps_delta}")

    if (
        int(current.get("scan_success", 0)) == 0
        and int(previous.get("scan_success", 0)) > 0
    ):
        score += 4
        reasons.append("scan_success_drop_to_zero")

    if int(current.get("scan_failures", 0)) > int(previous.get("scan_failures", 0)):
        score += 2
        reasons.append("scan_failures_increase")

    return score, reasons


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank anomalous scan pairs")
    _ = parser.add_argument("--input-summary", required=True)
    _ = parser.add_argument("--output-dir", default=".tmp")
    _ = parser.add_argument("--root-tenant", required=True)
    _ = parser.add_argument("--project-uuid", required=True)
    _ = parser.add_argument(
        "--pair-mode",
        choices=["adjacent", "best-anomaly", "latest"],
        default="best-anomaly",
    )
    _ = parser.add_argument("--min-delta-findings", type=int, default=10)
    _ = parser.add_argument("--min-delta-deps", type=int, default=50)
    _ = parser.add_argument("--timestamped", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    summary = load_json(Path(args.input_summary))
    items = summary.get("scan_results_summary", [])
    if len(items) < 2:
        raise ValueError("Need at least two scan results to build scan pairs")
    ranked: list[dict[str, Any]] = []
    for idx in range(len(items) - 1):
        current = items[idx]
        previous = items[idx + 1]
        score, reasons = anomaly_score(
            current,
            previous,
            min_delta_findings=args.min_delta_findings,
            min_delta_deps=args.min_delta_deps,
        )
        ranked.append(
            {
                "score": score,
                "reasons": reasons,
                "primary_scan_result_uuid": current.get("uuid"),
                "secondary_scan_result_uuid": previous.get("uuid"),
                "primary": current,
                "secondary": previous,
            }
        )

    latest_pair = ranked[0]
    ranked.sort(key=lambda item: item["score"], reverse=True)
    if args.pair_mode == "best-anomaly":
        selected = ranked[:1]
    elif args.pair_mode == "latest":
        selected = [latest_pair]
    else:
        selected = ranked
    regression_detected = bool(selected and selected[0]["score"] > 0)
    payload: dict[str, Any] = {
        "root_tenant": args.root_tenant,
        "project_uuid": args.project_uuid,
        "pair_mode": args.pair_mode,
        "candidate_pair_count": len(ranked),
        "selected_pairs": selected,
        "regression_detected": regression_detected,
    }
    artifact = write_json(
        output_dir=Path(args.output_dir),
        root_tenant_name=args.root_tenant,
        object_kind="scan_result_pairs",
        object_uuid=args.project_uuid,
        purpose="pairs",
        payload=payload,
        timestamped=args.timestamped,
    )
    payload["artifact"] = str(artifact)
    return payload


def main() -> int:
    args = build_parser().parse_args()
    result = run(args)
    print(result["artifact"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
