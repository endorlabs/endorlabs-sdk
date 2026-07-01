#!/usr/bin/env python3
"""Classify tenant Projects as CLI vs Cloud Scan and write the standard CSV."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.workflows.projects.inventory import (
    INSTALLATION_LIST_MASK,
    fetch_installation_lookup,
    fetch_latest_scan_execution_labels,
    installation_display_name,
    is_mixed_registration_execution,
    registration_source_label,
)

CSV_FIELDS = [
    "project name",
    "namespace",
    "uuid",
    "source",
    "latest scan execution",
    "mixed mode",
    "external_installation_id",
    "installation name",
]

PROJECT_MASK = (
    "meta.name,tenant_meta.namespace,uuid,"
    "spec.git.external_installation_id,spec.git.invalid_installation,spec.sbom"
)


def project_name(row: dict[str, Any]) -> str:
    return (row.get("meta") or {}).get("name") or ""


def project_namespace(row: dict[str, Any]) -> str:
    return (row.get("tenant_meta") or {}).get("namespace") or ""


def external_installation_id(row: dict[str, Any]) -> str:
    value = (row.get("spec") or {}).get("git", {}).get("external_installation_id")
    return str(value) if value else ""


def invalid_installation(row: dict[str, Any]) -> bool:
    return bool((row.get("spec") or {}).get("git", {}).get("invalid_installation"))


def row_to_csv(
    client: endorlabs.Client,
    row: dict[str, Any],
    installation_lookup: dict[str, dict[str, Any]],
    *,
    scan_execution: str,
) -> dict[str, str]:
    inst_id = external_installation_id(row)
    installation = installation_lookup.get(inst_id) if inst_id else None
    registration = registration_source_label(client, row)
    mixed = is_mixed_registration_execution(registration, scan_execution)
    return {
        "project name": project_name(row),
        "namespace": project_namespace(row),
        "uuid": row.get("uuid") or "",
        "source": registration,
        "latest scan execution": scan_execution,
        "mixed mode": "true" if mixed else "false",
        "external_installation_id": inst_id,
        "installation name": installation_display_name(installation),
    }


def build_summary(
    rows: list[dict[str, str]],
    *,
    tenant: str,
    sbom_excluded: int,
) -> dict[str, Any]:
    registration_counts = Counter(r["source"] for r in rows)
    execution_counts = Counter(r["latest scan execution"] for r in rows)
    install_counts: Counter[str] = Counter()
    install_names: dict[str, str] = {}
    for row in rows:
        if row["source"] != "Cloud Scan":
            continue
        inst_id = row["external_installation_id"]
        if not inst_id:
            continue
        install_counts[inst_id] += 1
        install_names[inst_id] = row["installation name"]

    cli_rows = [r for r in rows if r["source"] == "CLI"]
    cli_execution_rows = [r for r in rows if r["latest scan execution"] == "CLI"]
    mixed_rows = [r for r in rows if r["mixed mode"] == "true"]
    invalid_cloud = sum(
        1
        for project in rows
        if project["source"] == "Cloud Scan"
        and project.get("_invalid_installation") == "True"
    )

    ns_mode: dict[str, dict[str, int]] = defaultdict(lambda: Counter())
    for row in rows:
        ns_mode[row["namespace"]][row["source"]] += 1

    return {
        "tenant": tenant,
        "total_projects": len(rows),
        "sbom_projects_excluded": sbom_excluded,
        "registration_source_counts": dict(registration_counts),
        "source_counts": dict(registration_counts),
        "latest_scan_execution_counts": dict(execution_counts),
        "mixed_mode_count": len(mixed_rows),
        "mixed_mode_projects": [
            {
                "project name": r["project name"],
                "namespace": r["namespace"],
                "uuid": r["uuid"],
                "registration": r["source"],
                "latest scan execution": r["latest scan execution"],
            }
            for r in mixed_rows
        ],
        "cloud_invalid_installation_count": invalid_cloud,
        "installation_counts": [
            {
                "external_installation_id": inst_id,
                "installation name": install_names.get(inst_id, ""),
                "project_count": count,
            }
            for inst_id, count in install_counts.most_common()
        ],
        "cli_projects": [
            {
                "project name": r["project name"],
                "namespace": r["namespace"],
                "uuid": r["uuid"],
            }
            for r in cli_rows
        ],
        "cli_latest_scan_projects": [
            {
                "project name": r["project name"],
                "namespace": r["namespace"],
                "uuid": r["uuid"],
                "registration": r["source"],
            }
            for r in cli_execution_rows
        ],
        "namespace_breakdown": {
            ns: dict(counts)
            for ns, counts in sorted(
                ns_mode.items(),
                key=lambda item: sum(item[1].values()),
                reverse=True,
            )
        },
    }


def write_csv(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    csv_rows = [{field: row[field] for field in CSV_FIELDS} for row in rows]
    csv_rows.sort(
        key=lambda r: (
            r["mixed mode"] == "true",
            r["source"],
            r["namespace"].lower(),
            r["project name"].lower(),
        ),
        reverse=True,
    )
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(csv_rows)


def print_summary(summary: dict[str, Any], output: Path) -> None:
    registration = summary.get("registration_source_counts") or {}
    execution = summary.get("latest_scan_execution_counts") or {}
    cloud = registration.get("Cloud Scan", 0)
    cli = registration.get("CLI", 0)
    print(f"Tenant: {summary['tenant']}")
    print(
        f"Projects classified: {summary['total_projects']} "
        f"({summary['sbom_projects_excluded']} SBOM excluded from scan)"
    )
    print(f"Registration: Cloud Scan={cloud}, CLI={cli}")
    print(
        "Latest scan execution: "
        + ", ".join(f"{label}={count}" for label, count in sorted(execution.items()))
    )
    mixed = summary.get("mixed_mode_count", 0)
    if mixed:
        print(f"Mixed mode (registration != latest scan): {mixed}")
    invalid = summary.get("cloud_invalid_installation_count", 0)
    if invalid:
        print(f"Cloud projects with invalid_installation=True: {invalid}")
    installations = summary.get("installation_counts") or []
    if installations:
        print("Cloud installations:")
        for item in installations:
            label = item.get("installation name") or item["external_installation_id"]
            print(
                f"  {label}: {item['project_count']} projects "
                f"(external_installation_id={item['external_installation_id']})"
            )
    cli_projects = summary.get("cli_projects") or []
    if cli_projects:
        print("CLI-registered projects:")
        for item in cli_projects:
            print(f"  {item['project name']} [{item['namespace']}] ({item['uuid']})")
    cli_scan = summary.get("cli_latest_scan_projects") or []
    if cli_scan:
        print("Projects whose latest scan ran via CLI:")
        for item in cli_scan:
            reg = item.get("registration", "")
            suffix = f" (registered {reg})" if reg else ""
            print(
                f"  {item['project name']} [{item['namespace']}] "
                f"({item['uuid']}){suffix}"
            )
    print(f"Wrote {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", required=True, help="Tenant root namespace")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV output path (default: workspace exports/cli-vs-cloud/<tenant>-cli-vs-cloud.csv)",
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
        help="Optional cap on list pagination depth",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=12,
        help="Parallel workers for latest ScanResult lookup per project",
    )
    parser.add_argument(
        "--skip-scan-enrichment",
        action="store_true",
        help="Skip latest ScanResult RunBySystem lookup (registration only)",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        help="Optional path to write machine-readable summary JSON",
    )
    args = parser.parse_args()

    output = args.output or Path(
        f".endorlabs-context/workspace/sessions/agent/exports/cli-vs-cloud/"
        f"{args.tenant}-cli-vs-cloud.csv"
    )

    client = endorlabs.Client(tenant=args.tenant)

    list_kwargs: dict[str, Any] = {}
    if args.max_pages is not None:
        list_kwargs["max_pages"] = args.max_pages

    installation_lookup = fetch_installation_lookup(
        client,
        mask=INSTALLATION_LIST_MASK,
        **list_kwargs,
    )

    project_kwargs: dict[str, Any] = {
        "traverse": True,
        "mask": PROJECT_MASK,
        **list_kwargs,
    }
    projects = list(client.Project.list_iter(**project_kwargs))
    if args.project_uuid:
        wanted = set(args.project_uuid)
        projects = [row for row in projects if row.get("uuid") in wanted]

    sbom_count = sum(1 for row in projects if client.Project.is_sbom(row))
    eligible = [row for row in projects if not client.Project.is_sbom(row)]

    scan_labels: dict[str, str] = {}
    if not args.skip_scan_enrichment:
        scan_labels = fetch_latest_scan_execution_labels(
            client,
            eligible,
            max_workers=args.max_workers,
        )

    rows: list[dict[str, str]] = []
    for project in eligible:
        uuid = project.get("uuid") or ""
        execution = scan_labels.get(uuid, "unknown")
        csv_row = row_to_csv(
            client,
            project,
            installation_lookup,
            scan_execution=execution,
        )
        csv_row["_invalid_installation"] = str(invalid_installation(project))
        rows.append(csv_row)

    write_csv(rows, output)

    summary = build_summary(rows, tenant=args.tenant, sbom_excluded=sbom_count)
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summary, indent=2) + "\n")

    print_summary(summary, output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
