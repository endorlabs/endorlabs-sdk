"""Diff selected scan results and associated logs."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    from scripts.troubleshooting_scans.common import (
        build_api_client,
        load_json,
        root_tenant,
        scan_result_metrics,
        write_json,
        write_text,
    )
except ModuleNotFoundError:
    from common import (
        build_api_client,
        load_json,
        root_tenant,
        scan_result_metrics,
        write_json,
        write_text,
    )


KEYS_TO_DIFF = [
    "status",
    "exit_code",
    "scan_success",
    "scan_failures",
    "findings_critical",
    "findings_high",
    "findings_medium",
    "findings_low",
    "dependency_analysis_num_full",
    "dependency_analysis_num_approximate",
    "dependency_count_total",
    "endorctl_version",
    "sha",
    "ref",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diff two scan results")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--input-pairs", required=True)
    parser.add_argument("--input-logs-index")
    parser.add_argument("--output-dir", default=".tmp")
    parser.add_argument("--timestamped", action="store_true")
    return parser


def fetch_scan_result(api: Any, namespace: str, scan_uuid: str) -> dict[str, Any]:
    """Fetch one scan result by UUID."""
    resp = api.get(f"v1/namespaces/{namespace}/scan-results/{scan_uuid}")
    return resp.json()


def compute_diff(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    """Compute normalized field-level diff."""
    p = scan_result_metrics(primary)
    s = scan_result_metrics(secondary)
    changes = {}
    for key in KEYS_TO_DIFF:
        if p.get(key) != s.get(key):
            changes[key] = {"primary": p.get(key), "secondary": s.get(key)}
    return {"primary": p, "secondary": s, "changes": changes}


def build_markdown(diff_payload: dict[str, Any]) -> str:
    """Create a concise markdown report."""
    primary = diff_payload["primary"]
    secondary = diff_payload["secondary"]
    lines = [
        "# Scan Diff Report",
        "",
        f"- Primary scan: `{primary.get('uuid')}`",
        f"- Secondary scan: `{secondary.get('uuid')}`",
        f"- Primary status: `{primary.get('status')}`",
        f"- Secondary status: `{secondary.get('status')}`",
        "",
        "## Changed Fields",
    ]
    for key, value in diff_payload["changes"].items():
        lines.append(f"- `{key}`: `{value['secondary']}` -> `{value['primary']}`")
    if not diff_payload["changes"]:
        lines.append("- No changes in tracked fields.")
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> dict[str, Any]:
    pairs = load_json(Path(args.input_pairs))
    selected = pairs.get("selected_pairs", [])
    if not selected:
        raise ValueError("No selected pairs in input file")
    first = selected[0]
    primary_uuid = first["primary_scan_result_uuid"]
    secondary_uuid = first["secondary_scan_result_uuid"]

    api = build_api_client()
    primary = fetch_scan_result(api, args.namespace, primary_uuid)
    secondary = fetch_scan_result(api, args.namespace, secondary_uuid)
    diff_payload = compute_diff(primary, secondary)

    root = root_tenant(args.tenant)
    base_uuid = f"{primary_uuid}__vs__{secondary_uuid}"
    output_dir = Path(args.output_dir)
    report_payload = {
        "root_tenant": root,
        "namespace": args.namespace,
        "primary_scan_result_uuid": primary_uuid,
        "secondary_scan_result_uuid": secondary_uuid,
        "diff": diff_payload,
    }
    json_artifact = write_json(
        output_dir=output_dir,
        root_tenant_name=root,
        object_kind="scan_diff",
        object_uuid=base_uuid,
        purpose="report",
        payload=report_payload,
        timestamped=args.timestamped,
    )
    md_artifact = write_text(
        output_dir=output_dir,
        root_tenant_name=root,
        object_kind="scan_diff",
        object_uuid=base_uuid,
        purpose="report",
        text=build_markdown(diff_payload),
        extension=".md",
        timestamped=args.timestamped,
    )
    report_payload["json_artifact"] = str(json_artifact)
    report_payload["md_artifact"] = str(md_artifact)
    return report_payload


def main() -> int:
    args = build_parser().parse_args()
    result = run(args)
    print(result["json_artifact"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
