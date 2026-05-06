"""Fetch scan logs for selected scan result UUIDs."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .common import (
    build_api_client,
    build_scanlogs_client,
    load_json,
    root_tenant,
    write_json,
    write_text,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch scan logs for selected scans")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--project-uuid", required=True)
    parser.add_argument("--input-pairs", required=True)
    parser.add_argument("--max-entries", type=int, default=500)
    parser.add_argument("--output-dir", default=".tmp")
    parser.add_argument("--timestamped", action="store_true")
    return parser


def pull_embedded_logs(api: Any, namespace: str, scan_result_uuid: str) -> list[str]:
    """Fallback to scan-result embedded logs if ScanLogRequest returns nothing."""
    resp = api.get(f"v1/namespaces/{namespace}/scan-results/{scan_result_uuid}")
    result = resp.json()
    return (result.get("spec") or {}).get("logs") or []


def run(args: argparse.Namespace) -> dict[str, Any]:
    pair_payload = load_json(Path(args.input_pairs))
    selected_pairs = pair_payload.get("selected_pairs", [])
    if not selected_pairs:
        raise ValueError("No selected pairs found in input")

    root = root_tenant(args.tenant)
    output_dir = Path(args.output_dir)
    scanlogs_client = build_scanlogs_client(args.namespace)
    api = build_api_client()

    uuids: list[str] = []
    first = selected_pairs[0]
    for key in ("primary_scan_result_uuid", "secondary_scan_result_uuid"):
        value = first.get(key)
        if value and value not in uuids:
            uuids.append(value)

    index_entries: list[dict[str, Any]] = []
    for scan_uuid in uuids:
        entries: list[str] = []
        try:
            log_messages = scanlogs_client.ScanLogs.get_logs(
                scan_result_uuid=scan_uuid,
                namespace=args.namespace,
                max_entries=args.max_entries,
            )
            for message in log_messages:
                level = str(getattr(message, "log_level", "UNKNOWN"))
                ts = getattr(message, "timestamp", "")
                txt = getattr(message, "message", "")
                entries.append(f"{ts} [{level}] {txt}")
        except Exception:
            entries = []

        if not entries:
            entries = pull_embedded_logs(api, args.namespace, scan_uuid)

        text_blob = "\n".join(entries)
        log_artifact = write_text(
            output_dir=output_dir,
            root_tenant_name=root,
            object_kind="scan_log",
            object_uuid=scan_uuid,
            purpose="log",
            text=text_blob,
            extension=".txt",
            timestamped=args.timestamped,
        )
        index_entries.append(
            {
                "scan_result_uuid": scan_uuid,
                "namespace": args.namespace,
                "entry_count": len(entries),
                "log_artifact": str(log_artifact),
            }
        )

    index_payload = {
        "root_tenant": root,
        "project_uuid": args.project_uuid,
        "namespace": args.namespace,
        "logs": index_entries,
    }
    index_artifact = write_json(
        output_dir=output_dir,
        root_tenant_name=root,
        object_kind="scan_logs",
        object_uuid=args.project_uuid,
        purpose="index",
        payload=index_payload,
        timestamped=args.timestamped,
    )
    index_payload["artifact"] = str(index_artifact)
    return index_payload


def main() -> int:
    args = build_parser().parse_args()
    result = run(args)
    print(result["artifact"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
