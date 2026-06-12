"""Pull the full available log set for one scan result.

Uses ``ScanResult.get_logs`` with pagination (moving start_time cursor). Optionally
writes machine-readable JSON to ``--output-dir`` using the troubleshooting
filename contract.

Workflow position: run after ScanResult triage (see troubleshooting-scans skill).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.workflows.estate.collect.bounds import (
    is_list_truncated,
    resolve_max_pages,
)

from .common import (
    root_tenant,
    write_json,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pull full logs for a scan result UUID."
    )
    _ = parser.add_argument("--tenant", required=True, help="Root tenant namespace")
    _ = parser.add_argument(
        "--namespace",
        default=None,
        help=(
            "Namespace for scan lookup/requests. "
            "If omitted, resolved from project/scan."
        ),
    )
    _ = parser.add_argument(
        "--project-uuid",
        default=None,
        help="Optional project UUID. If omitted, auto-select first project with scans.",
    )
    _ = parser.add_argument(
        "--scan-result-uuid",
        default=None,
        help=(
            "Optional explicit scan UUID. "
            "If omitted, uses latest scan for resolved project."
        ),
    )
    _ = parser.add_argument(
        "--project-query",
        default="",
        help="Optional name/uuid substring used by auto-select (demo-like behavior).",
    )
    _ = parser.add_argument(
        "--project-list-max-pages",
        type=int,
        default=0,
        help="Max pages when auto-selecting a project (0 = unlimited).",
    )
    _ = parser.add_argument("--project-list-page-size", type=int, default=100)
    _ = parser.add_argument("--batch-size", type=int, default=500)
    _ = parser.add_argument("--max-rounds", type=int, default=50)
    _ = parser.add_argument("--start-time", default=None, help="ISO8601 optional")
    _ = parser.add_argument("--end-time", default=None, help="ISO8601 optional")
    _ = parser.add_argument(
        "--compact",
        action="store_true",
        help="Print single-line JSON suitable for piping.",
    )
    _ = parser.add_argument(
        "--output-dir",
        default=None,
        help="If set, write JSON artifact here (else stdout only).",
    )
    _ = parser.add_argument(
        "--timestamped",
        action="store_true",
        help="Append timestamp to artifact filename when using --output-dir",
    )
    return parser.parse_args()


def _iso_to_dt(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(UTC)


def _dt_to_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _project_name(project: Any) -> str:
    meta = getattr(project, "meta", None)
    return getattr(meta, "name", "") or str(getattr(project, "uuid", ""))


def _project_namespace(project: Any) -> str | None:
    tenant_meta = getattr(project, "tenant_meta", None)
    ns = getattr(tenant_meta, "namespace", None)
    return str(ns) if ns else None


def _select_project(
    client: endorlabs.Client,
    tenant: str,
    query: str,
    *,
    list_max_pages: int | None,
    page_size: int,
) -> tuple[Any, bool]:
    projects = client.Project.list(
        namespace=tenant,
        traverse=True,
        max_pages=list_max_pages,
        page_size=page_size,
    )
    truncated = is_list_truncated(
        len(projects), max_pages=list_max_pages, page_size=page_size
    )
    q = query.strip().lower()
    for project in projects[:80]:
        name = _project_name(project).lower()
        uuid = str(getattr(project, "uuid", "")).lower()
        if q and q not in name and q not in uuid:
            continue
        scans = client.ScanResult.list(parent=project, max_pages=1, page_size=1)
        if scans:
            return project, truncated
    raise ValueError(
        "No eligible project with scan results found for this tenant/query."
    )


def _resolve_latest_scan_for_project(client: endorlabs.Client, project: Any) -> Any:
    scans = client.ScanResult.list(
        parent=project,
        sort_by="meta.create_time",
        desc=True,
        max_pages=1,
        page_size=1,
    )
    if not scans:
        raise ValueError("Resolved project has no scan results.")
    return scans[0]


def _dedupe_key(message: Any) -> tuple[str | None, str]:
    payload = getattr(message, "json_payload", None)
    payload_s = (
        json.dumps(payload, sort_keys=True, ensure_ascii=True) if payload else ""
    )
    return getattr(message, "timestamp", None), payload_s


def _iter_logs(
    client: endorlabs.Client,
    *,
    namespace: str,
    scan_result_uuid: str,
    batch_size: int,
    max_rounds: int,
    start_time: str | None,
    end_time: str | None,
) -> tuple[list[Any], int]:
    cursor = start_time
    seen: set[tuple[str | None, str]] = set()
    all_messages: list[Any] = []
    rounds = 0

    while rounds < max_rounds:
        rounds += 1
        batch = client.ScanResult.get_logs(
            scan_result_uuid,
            namespace=namespace,
            max_entries=batch_size,
            start_time=cursor,
            end_time=end_time,
            newest_first=False,
        )
        if not batch:
            break

        new_count = 0
        last_ts: str | None = None
        for message in batch:
            last_ts = getattr(message, "timestamp", last_ts)
            key = _dedupe_key(message)
            if key in seen:
                continue
            seen.add(key)
            all_messages.append(message)
            new_count += 1

        if new_count == 0:
            break
        if len(batch) < batch_size or not last_ts:
            break

        cursor = _dt_to_iso(_iso_to_dt(last_ts) + timedelta(milliseconds=1))

    return all_messages, rounds


def _message_to_dict(message: Any) -> dict[str, Any]:
    return {
        "timestamp": getattr(message, "timestamp", None),
        "level": (
            getattr(getattr(message, "level", None), "value", None)
            or str(getattr(message, "level", "") or "")
        ),
        "json_payload": getattr(message, "json_payload", None),
        "tags": getattr(message, "tags", None),
    }


def main() -> int:
    """Run the module CLI and return exit code."""
    args = _parse_args()
    client = endorlabs.Client(tenant=args.tenant)
    try:
        project: Any | None = None
        project_list_truncated = False
        resolved_namespace = args.namespace
        scan: Any | None = None
        scan_uuid: str

        if args.scan_result_uuid:
            scan_uuid = args.scan_result_uuid
            if not resolved_namespace:
                scan = client.ScanResult.get(scan_uuid, namespace=args.tenant)
                tm = getattr(scan, "tenant_meta", None)
                resolved_namespace = (
                    getattr(tm, "namespace", None) if tm else None
                ) or str(args.tenant)
            else:
                scan = client.ScanResult.get(scan_uuid, namespace=resolved_namespace)
        else:
            if args.project_uuid:
                ns_for_get = resolved_namespace or args.tenant
                project = client.Project.get(args.project_uuid, namespace=ns_for_get)
                if project is None:
                    raise ValueError("Project UUID not found in provided scope.")
            else:
                project, project_list_truncated = _select_project(
                    client,
                    args.tenant,
                    args.project_query,
                    list_max_pages=resolve_max_pages(args.project_list_max_pages),
                    page_size=args.project_list_page_size,
                )
            resolved_namespace = resolved_namespace or _project_namespace(project)
            if not resolved_namespace:
                raise ValueError("Could not resolve namespace from project.")
            scan = _resolve_latest_scan_for_project(client, project)
            resolved_scan_uuid = getattr(scan, "uuid", None)
            if not resolved_scan_uuid:
                raise ValueError("Resolved latest scan is missing uuid.")
            scan_uuid = str(resolved_scan_uuid)

        start_time = args.start_time
        if not start_time and scan and getattr(scan, "spec", None):
            scan_start = getattr(scan.spec, "start_time", None)
            if isinstance(scan_start, str) and scan_start:
                start_time = _dt_to_iso(_iso_to_dt(scan_start) - timedelta(hours=1))
        end_time = args.end_time or _dt_to_iso(datetime.now(UTC))

        messages, rounds = _iter_logs(
            client,
            namespace=resolved_namespace,
            scan_result_uuid=scan_uuid,
            batch_size=args.batch_size,
            max_rounds=args.max_rounds,
            start_time=start_time,
            end_time=end_time,
        )

        parent_uuid = None
        if scan and getattr(scan, "meta", None):
            parent_uuid = getattr(scan.meta, "parent_uuid", None)

        payload: dict[str, Any] = {
            "tenant": args.tenant,
            "namespace": resolved_namespace,
            "project_uuid": getattr(project, "uuid", None) if project else parent_uuid,
            "project_name": _project_name(project) if project else None,
            "scan_result_uuid": scan_uuid,
            "start_time": start_time,
            "end_time": end_time,
            "batch_size": args.batch_size,
            "rounds": rounds,
            "count": len(messages),
            "project_list_truncated": project_list_truncated,
            "messages": [_message_to_dict(m) for m in messages],
        }

        if args.output_dir:
            rt = root_tenant(str(args.tenant))
            path = write_json(
                output_dir=Path(args.output_dir),
                root_tenant_name=rt,
                object_kind="scan_logs_pull",
                object_uuid=scan_uuid,
                purpose="full",
                payload=payload,
                timestamped=args.timestamped,
            )
            print(str(path), file=sys.stderr)
        elif args.compact:
            print(json.dumps(payload, separators=(",", ":"), ensure_ascii=True))
        else:
            print(json.dumps(payload, indent=2))
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
