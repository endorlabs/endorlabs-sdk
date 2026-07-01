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

CSV_FIELDS = [
    "project name",
    "namespace",
    "uuid",
    "source",
    "external_installation_id",
    "installation name",
]

PROJECT_MASK = (
    "meta.name,tenant_meta.namespace,uuid,"
    "spec.git.external_installation_id,spec.git.invalid_installation,spec.sbom"
)
INSTALLATION_MASK = "meta.name,tenant_meta.namespace,uuid,spec.external_id,spec.external_name,spec.login"


def project_name(row: dict[str, Any]) -> str:
    return (row.get("meta") or {}).get("name") or ""


def project_namespace(row: dict[str, Any]) -> str:
    return (row.get("tenant_meta") or {}).get("namespace") or ""


def project_source(row: dict[str, Any]) -> str:
    inst = (row.get("spec") or {}).get("git", {}).get("external_installation_id")
    return "Cloud Scan" if inst else "CLI"


def external_installation_id(row: dict[str, Any]) -> str:
    value = (row.get("spec") or {}).get("git", {}).get("external_installation_id")
    return str(value) if value else ""


def invalid_installation(row: dict[str, Any]) -> bool:
    return bool((row.get("spec") or {}).get("git", {}).get("invalid_installation"))


def is_sbom_project(row: dict[str, Any]) -> bool:
    return (row.get("spec") or {}).get("sbom") is not None


def build_installation_lookup(
    installations: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in installations:
        ext_id = (row.get("spec") or {}).get("external_id")
        if ext_id:
            lookup[str(ext_id)] = row
    return lookup


def installation_name(installation: dict[str, Any] | None) -> str:
    if not installation:
        return ""
    spec = installation.get("spec") or {}
    meta_name = (installation.get("meta") or {}).get("name") or ""
    external_name = spec.get("external_name") or ""
    login = spec.get("login") or ""
    if external_name:
        return external_name
    if meta_name and login:
        return f"{meta_name} ({login})"
    return meta_name or login


def row_to_csv(
    row: dict[str, Any],
    installation_lookup: dict[str, dict[str, Any]],
) -> dict[str, str]:
    inst_id = external_installation_id(row)
    installation = installation_lookup.get(inst_id) if inst_id else None
    return {
        "project name": project_name(row),
        "namespace": project_namespace(row),
        "uuid": row.get("uuid") or "",
        "source": project_source(row),
        "external_installation_id": inst_id,
        "installation name": installation_name(installation),
    }


def build_summary(
    rows: list[dict[str, str]],
    *,
    tenant: str,
    sbom_excluded: int,
) -> dict[str, Any]:
    mode_counts = Counter(r["source"] for r in rows)
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
        "source_counts": dict(mode_counts),
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
        key=lambda r: (r["source"], r["namespace"].lower(), r["project name"].lower())
    )
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(csv_rows)


def print_summary(summary: dict[str, Any], output: Path) -> None:
    source_counts = summary.get("source_counts") or {}
    cloud = source_counts.get("Cloud Scan", 0)
    cli = source_counts.get("CLI", 0)
    print(f"Tenant: {summary['tenant']}")
    print(
        f"Projects classified: {summary['total_projects']} "
        f"({summary['sbom_projects_excluded']} SBOM excluded from scan)"
    )
    print(f"Source counts: Cloud Scan={cloud}, CLI={cli}")
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
        print("CLI projects:")
        for item in cli_projects:
            print(f"  {item['project name']} [{item['namespace']}] ({item['uuid']})")
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

    installation_kwargs: dict[str, Any] = {
        "traverse": True,
        "mask": INSTALLATION_MASK,
    }
    project_kwargs: dict[str, Any] = {
        "traverse": True,
        "mask": PROJECT_MASK,
    }
    if args.max_pages is not None:
        installation_kwargs["max_pages"] = args.max_pages
        project_kwargs["max_pages"] = args.max_pages

    installations = list(client.Installation.list_iter(**installation_kwargs))
    installation_lookup = build_installation_lookup(installations)

    projects = list(client.Project.list_iter(**project_kwargs))
    if args.project_uuid:
        wanted = set(args.project_uuid)
        projects = [row for row in projects if row.get("uuid") in wanted]

    sbom_count = sum(1 for row in projects if is_sbom_project(row))
    eligible = [row for row in projects if not is_sbom_project(row)]

    rows: list[dict[str, str]] = []
    for project in eligible:
        csv_row = row_to_csv(project, installation_lookup)
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
