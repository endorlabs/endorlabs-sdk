"""Fetch scan logs for selected scan result UUIDs."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from endorlabs.client_surface import Client
from endorlabs.utils.logging_config import get_resource_logger

from .common import (
    default_troubleshooting_output_dir,
    load_json,
    root_tenant,
    scanlog_line,
    write_json,
    write_text,
)

_LOGGER = get_resource_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build argparse parser for this workflow CLI."""
    parser = argparse.ArgumentParser(description="Fetch scan logs for selected scans")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--project-uuid", required=True)
    parser.add_argument("--input-pairs", required=True)
    parser.add_argument("--max-entries", type=int, default=500)
    parser.add_argument("--output-dir", default=default_troubleshooting_output_dir())
    parser.add_argument("--timestamped", action="store_true")
    return parser


def pull_embedded_logs(
    client: Client, namespace: str, scan_result_uuid: str
) -> list[str]:
    """Fallback to scan-result embedded logs if ScanLogRequest returns nothing."""
    scan_result = client.ScanResult.get(scan_result_uuid, namespace=namespace)
    spec = getattr(scan_result, "spec", None)
    logs = getattr(spec, "logs", None) if spec is not None else None
    return list(logs or [])


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Execute workflow from parsed CLI args."""
    pair_payload = load_json(Path(args.input_pairs))
    selected_pairs = pair_payload.get("selected_pairs", [])
    if not selected_pairs:
        raise ValueError("No selected pairs found in input")

    root = root_tenant(args.tenant)
    output_dir = Path(args.output_dir)
    scanlogs_client = Client(tenant=args.namespace)

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
            log_messages = scanlogs_client.ScanResult.get_logs(
                scan_uuid,
                namespace=args.namespace,
                max_entries=args.max_entries,
            )
            entries.extend(scanlog_line(message) for message in log_messages)
        except Exception as exc:
            _LOGGER.warning(
                "ScanResult.get_logs failed for %s: %s", scan_uuid, exc, exc_info=True
            )
            entries = []

        if not entries:
            entries = pull_embedded_logs(scanlogs_client, args.namespace, scan_uuid)

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
    """Run the module CLI and return exit code."""
    args = build_parser().parse_args()
    result = run(args)
    print(result["artifact"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
