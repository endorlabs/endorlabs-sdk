#!/usr/bin/env python3
"""Audit tenant projects by latest CLI endorctl version (recent scan window)."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.context.paths import default_runs_dir, sanitize_path_segment
from endorlabs.tools.list_sharding import ProjectShard, parallel_map_shards
from endorlabs.workflows.projects.inventory import (
    extract_run_by_system,
    scan_execution_label,
)

RUN_BUCKET = "ci-endorctl-version-audit"


def default_ci_endorctl_csv(tenant: str) -> Path:
    safe = sanitize_path_segment(tenant)
    return default_runs_dir(RUN_BUCKET) / f"{safe}-ci-endorctl-versions.csv"


SCAN_AUDIT_MASK = (
    "spec.environment.config.RunBySystem,"
    "spec.environment.endorctl_version,"
    "meta.create_time"
)

PROJECT_MASK = "meta.name,tenant_meta.namespace,uuid,spec.sbom"

CSV_FIELDS = [
    "project name",
    "namespace",
    "uuid",
    "latest scan execution",
    "endorctl version",
    "latest scan time",
]

_VERSION_PREFIX_RE = re.compile(
    r"^(?:endorctl\s+version\s+)?v?(?P<version>\d+\.\d+\.\d+(?:[-+][\w.]+)?)$",
    re.IGNORECASE,
)


def project_name(row: dict[str, Any]) -> str:
    return (row.get("meta") or {}).get("name") or ""


def project_namespace(row: dict[str, Any]) -> str:
    return (row.get("tenant_meta") or {}).get("namespace") or ""


def project_uuid(row: dict[str, Any]) -> str:
    return str(row.get("uuid") or "")


def parse_create_time(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_endorctl_version(raw: str | None) -> str:
    if not raw:
        return "unknown"
    text = raw.strip()
    match = _VERSION_PREFIX_RE.match(text)
    if match:
        return match.group("version")
    return text


def version_matches(normalized: str, target: str) -> bool:
    target_norm = normalize_endorctl_version(target)
    return normalized == target_norm or normalized.startswith(f"{target_norm}-")


def extract_endorctl_version(scan_row: dict[str, Any]) -> str:
    environment = (scan_row.get("spec") or {}).get("environment") or {}
    if not isinstance(environment, dict):
        return "unknown"
    return normalize_endorctl_version(environment.get("endorctl_version"))


def latest_scan_row(
    client: endorlabs.Client, project_row: dict[str, Any]
) -> dict[str, Any] | None:
    scans = client.ScanResult.list_by_project(
        project_row,
        mask=SCAN_AUDIT_MASK,
        limit=1,
    )
    if not scans:
        return None
    row = scans[0]
    return row if isinstance(row, dict) else row.model_dump(mode="json")


def classify_latest_scan(
    scan_row: dict[str, Any] | None,
    *,
    cutoff: datetime,
) -> dict[str, Any] | None:
    if not scan_row:
        return None
    create_time = parse_create_time((scan_row.get("meta") or {}).get("create_time"))
    if create_time is None or create_time < cutoff:
        return None
    execution = scan_execution_label(extract_run_by_system(scan_row))
    if execution != "CLI":
        return None
    return {
        "execution": execution,
        "endorctl_version": extract_endorctl_version(scan_row),
        "latest_scan_time": create_time.isoformat(),
    }


def row_to_csv(project: dict[str, Any], audit: dict[str, Any]) -> dict[str, str]:
    return {
        "project name": project_name(project),
        "namespace": project_namespace(project),
        "uuid": project_uuid(project),
        "latest scan execution": audit["execution"],
        "endorctl version": audit["endorctl_version"],
        "latest scan time": audit["latest_scan_time"],
    }


def build_summary(
    rows: list[dict[str, str]],
    *,
    tenant: str,
    days: int,
    sbom_excluded: int,
    projects_considered: int,
    excluded_not_recent: int,
    excluded_non_cli_latest: int,
    excluded_no_scan: int,
    version_filter: str | None,
) -> dict[str, Any]:
    version_counts = Counter(row["endorctl version"] for row in rows)
    filtered_projects = rows
    if version_filter:
        filtered_projects = [
            row
            for row in rows
            if version_matches(row["endorctl version"], version_filter)
        ]

    return {
        "tenant": tenant,
        "lookback_days": days,
        "sbom_projects_excluded": sbom_excluded,
        "projects_considered": projects_considered,
        "excluded_no_scan": excluded_no_scan,
        "excluded_not_recent": excluded_not_recent,
        "excluded_non_cli_latest": excluded_non_cli_latest,
        "cli_projects_in_window": len(rows),
        "version_counts": dict(version_counts.most_common()),
        "version_filter": version_filter,
        "version_filter_project_count": len(filtered_projects),
        "version_filter_projects": [
            {
                "project name": row["project name"],
                "namespace": row["namespace"],
                "uuid": row["uuid"],
                "endorctl version": row["endorctl version"],
                "latest scan time": row["latest scan time"],
            }
            for row in filtered_projects
        ],
    }


def write_csv(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            row["endorctl version"],
            row["namespace"].lower(),
            row["project name"].lower(),
        ),
    )
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(sorted_rows)


def print_summary(summary: dict[str, Any], output: Path) -> None:
    print(f"Tenant: {summary['tenant']}")
    print(f"Lookback window: {summary['lookback_days']} days (latest scan must be CLI)")
    print(
        "Projects considered: "
        f"{summary['projects_considered']} "
        f"({summary['sbom_projects_excluded']} SBOM excluded)"
    )
    print(
        "Excluded: "
        f"no_scan={summary['excluded_no_scan']}, "
        f"not_recent={summary['excluded_not_recent']}, "
        f"non_cli_latest={summary['excluded_non_cli_latest']}"
    )
    print(f"CLI projects in window: {summary['cli_projects_in_window']}")
    print("endorctl version counts:")
    for version, count in (summary.get("version_counts") or {}).items():
        print(f"  {version}: {count}")
    version_filter = summary.get("version_filter")
    if version_filter:
        print(
            f"Projects on {version_filter}: "
            f"{summary.get('version_filter_project_count', 0)}"
        )
        for item in summary.get("version_filter_projects") or []:
            print(
                f"  {item['project name']} [{item['namespace']}] "
                f"({item['uuid']}) @ {item['latest scan time']}"
            )
    print(f"Wrote {output}")


def audit_projects(
    client: endorlabs.Client,
    projects: list[dict[str, Any]],
    *,
    cutoff: datetime,
    max_workers: int,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    by_uuid = {project_uuid(row): row for row in projects if project_uuid(row)}
    shards = [
        ProjectShard(project_uuid=uuid, namespace="", label=None) for uuid in by_uuid
    ]

    def _worker(shard: ProjectShard) -> tuple[str, dict[str, str] | None]:
        project = by_uuid[shard.project_uuid]
        scan_row = latest_scan_row(client, project)
        if scan_row is None:
            return "excluded_no_scan", None
        create_time = parse_create_time((scan_row.get("meta") or {}).get("create_time"))
        if create_time is None or create_time < cutoff:
            return "excluded_not_recent", None
        execution = scan_execution_label(extract_run_by_system(scan_row))
        if execution != "CLI":
            return "excluded_non_cli_latest", None
        audit = {
            "execution": execution,
            "endorctl_version": extract_endorctl_version(scan_row),
            "latest_scan_time": create_time.isoformat(),
        }
        return "included", row_to_csv(project, audit)

    outcomes = parallel_map_shards(
        shards,
        _worker,
        max_workers=max_workers,
        progress_label="CLI endorctl version audit",
    )
    excluded = Counter(status for status, _ in outcomes if status != "included")
    rows = [row for status, row in outcomes if status == "included" and row is not None]
    return rows, {
        "excluded_no_scan": excluded.get("excluded_no_scan", 0),
        "excluded_not_recent": excluded.get("excluded_not_recent", 0),
        "excluded_non_cli_latest": excluded.get("excluded_non_cli_latest", 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", required=True, help="Tenant root namespace")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Include projects whose latest scan is within this many days (default: 7)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "CSV output path (default: workspace/runs/ci-endorctl-version-audit/"
            "<tenant>-ci-endorctl-versions.csv)"
        ),
    )
    parser.add_argument(
        "--version",
        dest="version_filter",
        default=None,
        help="Optional endorctl version filter (e.g. 1.7.980) for project listing",
    )
    parser.add_argument(
        "--project-uuid",
        action="append",
        default=[],
        help="Optional project UUID filter (repeatable)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional cap on project list pagination depth",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=12,
        help="Parallel workers for latest ScanResult lookup per project",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        help="Optional path to write machine-readable summary JSON",
    )
    args = parser.parse_args()

    output = args.output or default_ci_endorctl_csv(args.tenant)

    client = endorlabs.Client(tenant=args.tenant)
    cutoff = datetime.now(tz=UTC) - timedelta(days=args.days)

    list_kwargs: dict[str, Any] = {"traverse": True, "mask": PROJECT_MASK}
    if args.max_pages is not None:
        list_kwargs["max_pages"] = args.max_pages

    projects = list(client.Project.list_iter(**list_kwargs))
    if args.project_uuid:
        wanted = set(args.project_uuid)
        projects = [row for row in projects if row.get("uuid") in wanted]

    sbom_count = sum(1 for row in projects if client.Project.is_sbom(row))
    eligible = [row for row in projects if not client.Project.is_sbom(row)]

    rows, excluded = audit_projects(
        client,
        eligible,
        cutoff=cutoff,
        max_workers=args.max_workers,
    )
    write_csv(rows, output)

    summary = build_summary(
        rows,
        tenant=args.tenant,
        days=args.days,
        sbom_excluded=sbom_count,
        projects_considered=len(eligible),
        version_filter=args.version_filter,
        **excluded,
    )
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summary, indent=2) + "\n")

    print_summary(summary, output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
