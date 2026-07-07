"""Build a user-supplied scan-result pair artifact for downstream diff/log steps."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .common import (
    default_troubleshooting_output_dir,
    parse_app_scan_history_url,
    root_tenant,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    """Build argparse parser for this workflow CLI."""
    parser = argparse.ArgumentParser(
        description="Build explicit scan pair JSON for diff/logs steps"
    )
    _ = parser.add_argument("--tenant", required=True)
    _ = parser.add_argument("--project-uuid", required=True)
    _ = parser.add_argument("--primary-scan-result-uuid")
    _ = parser.add_argument("--secondary-scan-result-uuid")
    _ = parser.add_argument("--primary-scan-result-url")
    _ = parser.add_argument("--secondary-scan-result-url")
    _ = parser.add_argument("--reason", default="user_supplied")
    _ = parser.add_argument(
        "--output-dir", default=default_troubleshooting_output_dir()
    )
    _ = parser.add_argument("--timestamped", action="store_true")
    return parser


def _resolve_scan_uuid(*, url: str | None, uuid: str | None, label: str) -> str:
    if uuid:
        return uuid.strip()
    if url:
        _, scan_uuid = parse_app_scan_history_url(url)
        return scan_uuid
    raise ValueError(f"Provide --{label}-scan-result-uuid or --{label}-scan-result-url")


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Execute workflow from parsed CLI args."""
    primary_uuid = _resolve_scan_uuid(
        url=args.primary_scan_result_url,
        uuid=args.primary_scan_result_uuid,
        label="primary",
    )
    secondary_uuid = _resolve_scan_uuid(
        url=args.secondary_scan_result_url,
        uuid=args.secondary_scan_result_uuid,
        label="secondary",
    )
    root = root_tenant(args.tenant)
    payload: dict[str, Any] = {
        "root_tenant": root,
        "project_uuid": args.project_uuid,
        "pair_mode": "user_supplied",
        "candidate_pair_count": 1,
        "selected_pairs": [
            {
                "score": 0,
                "reasons": [args.reason],
                "pair_mode": "user_supplied",
                "primary_scan_result_uuid": primary_uuid,
                "secondary_scan_result_uuid": secondary_uuid,
            }
        ],
        "regression_detected": True,
    }
    artifact = write_json(
        output_dir=Path(args.output_dir),
        root_tenant_name=root,
        object_kind="scan_result_pairs",
        object_uuid=args.project_uuid,
        purpose="pairs",
        payload=payload,
        timestamped=args.timestamped,
    )
    payload["artifact"] = str(artifact)
    return payload


def main() -> int:
    """Run the module CLI and return exit code."""
    args = build_parser().parse_args()
    result = run(args)
    print(result["artifact"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
