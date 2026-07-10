#!/usr/bin/env python3
"""Find potential duplicate Projects tenant-wide and write the standard CSV."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.context.paths import default_runs_dir, sanitize_path_segment
from endorlabs.workflows.projects.inventory import (
    fetch_latest_scan_execution_labels,
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
]


def canonical_name(name: str, *, strip_tokens: frozenset[str] | None = None) -> str:
    normalized = (name or "").strip().lower()
    if not strip_tokens:
        return normalized
    pattern = (
        r"[-_./]?("
        + "|".join(
            re.escape(token) for token in sorted(strip_tokens, key=len, reverse=True)
        )
        + r")[-_./]?"
    )
    return re.sub(pattern, "", normalized, flags=re.IGNORECASE)


def project_name(row: dict[str, Any]) -> str:
    return (row.get("meta") or {}).get("name") or ""


def project_namespace(row: dict[str, Any]) -> str:
    return (row.get("tenant_meta") or {}).get("namespace") or ""


def row_to_csv(
    client: endorlabs.Client,
    row: dict[str, Any],
    *,
    scan_execution: str,
) -> dict[str, str]:
    registration = registration_source_label(client, row)
    mixed = is_mixed_registration_execution(registration, scan_execution)
    return {
        "project name": project_name(row),
        "namespace": project_namespace(row),
        "uuid": row.get("uuid") or "",
        "source": registration,
        "latest scan execution": scan_execution,
        "mixed mode": "true" if mixed else "false",
    }


def merge_clusters(groups: list[list[dict[str, Any]]]) -> list[list[dict[str, Any]]]:
    parent: dict[str, str] = {}

    def find(uuid: str) -> str:
        parent.setdefault(uuid, uuid)
        if parent[uuid] != uuid:
            parent[uuid] = find(parent[uuid])
        return parent[uuid]

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    uuid_to_row: dict[str, dict[str, Any]] = {}
    for group in groups:
        uuids = [r.get("uuid") for r in group if r.get("uuid")]
        for row in group:
            if row.get("uuid"):
                uuid_to_row[row["uuid"]] = row
        for i in range(1, len(uuids)):
            union(uuids[0], uuids[i])

    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for uuid, row in uuid_to_row.items():
        clusters[find(uuid)].append(row)
    return [c for c in clusters.values() if len(c) >= 2]


def find_duplicate_groups(
    projects: list[dict[str, Any]],
    *,
    is_sbom: Any,
    strip_tokens: frozenset[str] | None = None,
) -> list[list[dict[str, Any]]]:
    eligible = [row for row in projects if not is_sbom(row)]
    candidate_groups: list[list[dict[str, Any]]] = []

    by_exact: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        by_exact[project_name(row)].append(row)
    for group in by_exact.values():
        namespaces = {project_namespace(r) for r in group}
        if len(namespaces) >= 2:
            candidate_groups.append(group)

    if strip_tokens:
        by_canonical: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in eligible:
            name = project_name(row)
            key = canonical_name(name, strip_tokens=strip_tokens)
            if key:
                by_canonical[key].append(row)
        for group in by_canonical.values():
            if len(group) >= 2:
                candidate_groups.append(group)

    return merge_clusters(candidate_groups)


def cluster_insights(
    clusters: list[list[dict[str, Any]]],
    csv_rows: list[dict[str, str]],
) -> dict[str, Any]:
    """Summarize registration vs scan-execution diversity inside duplicate clusters."""
    by_uuid = {row["uuid"]: row for row in csv_rows}
    mixed_clusters = 0
    registration_diverse = 0
    execution_diverse = 0
    for cluster in clusters:
        uuids = [r.get("uuid") for r in cluster if r.get("uuid")]
        rows = [by_uuid[uuid] for uuid in uuids if uuid in by_uuid]
        if not rows:
            continue
        registrations = {row["source"] for row in rows}
        executions = {row["latest scan execution"] for row in rows}
        if len(registrations) > 1:
            registration_diverse += 1
        if len(executions) > 1:
            execution_diverse += 1
        if any(row["mixed mode"] == "true" for row in rows):
            mixed_clusters += 1
    return {
        "clusters_with_mixed_mode_member": mixed_clusters,
        "clusters_with_diverse_registration": registration_diverse,
        "clusters_with_diverse_latest_scan": execution_diverse,
    }


def write_csv(
    client: endorlabs.Client,
    clusters: list[list[dict[str, Any]]],
    output: Path,
    *,
    scan_labels: dict[str, str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for cluster in clusters:
        for project in cluster:
            uuid = project.get("uuid") or ""
            execution = scan_labels.get(uuid, "unknown")
            rows.append(row_to_csv(client, project, scan_execution=execution))
    rows.sort(
        key=lambda r: (
            r["project name"].lower(),
            r["namespace"],
            r["mixed mode"] == "true",
        )
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


RUN_BUCKET = "duplicate-projects"


def default_duplicate_projects_csv(tenant: str) -> Path:
    safe = sanitize_path_segment(tenant)
    return default_runs_dir(RUN_BUCKET) / f"{safe}-duplicates.csv"


def parse_strip_tokens(raw: list[str]) -> frozenset[str] | None:
    tokens: set[str] = set()
    for item in raw:
        for part in item.split(","):
            token = part.strip()
            if token:
                tokens.add(token)
    return frozenset(tokens) if tokens else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", required=True, help="Tenant root namespace")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV output path (default: workspace/runs/duplicate-projects/<tenant>-duplicates.csv)",
    )
    parser.add_argument(
        "--name-strip-tokens",
        action="append",
        default=[],
        help=(
            "Optional whole-word tokens to strip for canonical-name clustering "
            "(repeatable or comma-separated; default: exact-name only)"
        ),
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
        help="Parallel workers for latest ScanResult lookup per duplicate row",
    )
    parser.add_argument(
        "--skip-scan-enrichment",
        action="store_true",
        help="Skip latest ScanResult RunBySystem lookup",
    )
    args = parser.parse_args()
    output = args.output or default_duplicate_projects_csv(args.tenant)

    client = endorlabs.Client(tenant=args.tenant)
    list_kwargs: dict[str, Any] = {
        "traverse": True,
        "mask": "meta.name,tenant_meta.namespace,uuid,spec.git.external_installation_id,spec.sbom",
    }
    if args.max_pages is not None:
        list_kwargs["max_pages"] = args.max_pages

    strip_tokens = parse_strip_tokens(args.name_strip_tokens)
    projects = list(client.Project.list_iter(**list_kwargs))
    sbom_count = sum(1 for p in projects if client.Project.is_sbom(p))
    clusters = find_duplicate_groups(
        projects,
        is_sbom=client.Project.is_sbom,
        strip_tokens=strip_tokens,
    )

    cluster_projects = [row for cluster in clusters for row in cluster]
    scan_labels: dict[str, str] = {}
    if not args.skip_scan_enrichment and cluster_projects:
        scan_labels = fetch_latest_scan_execution_labels(
            client,
            cluster_projects,
            max_workers=args.max_workers,
        )

    rows = write_csv(
        client,
        clusters,
        output,
        scan_labels=scan_labels,
    )

    eligible = len(projects) - sbom_count
    insights = cluster_insights(clusters, rows)
    registration_counts = Counter(row["source"] for row in rows)
    execution_counts = Counter(row["latest scan execution"] for row in rows)
    mixed_rows = sum(1 for row in rows if row["mixed mode"] == "true")

    print(
        f"Scanned {len(projects)} projects ({sbom_count} SBOM excluded, {eligible} eligible); "
        f"{len(clusters)} duplicate clusters; {len(rows)} CSV rows"
    )
    if rows:
        print(
            "Duplicate-row registration: "
            + ", ".join(f"{k}={v}" for k, v in sorted(registration_counts.items()))
        )
        print(
            "Duplicate-row latest scan: "
            + ", ".join(f"{k}={v}" for k, v in sorted(execution_counts.items()))
        )
        if mixed_rows:
            print(f"Duplicate rows in mixed mode: {mixed_rows}")
        if insights["clusters_with_diverse_latest_scan"]:
            print(
                "Clusters with diverse latest scan execution: "
                f"{insights['clusters_with_diverse_latest_scan']}"
            )
    if strip_tokens:
        print(f"Canonical strip tokens: {', '.join(sorted(strip_tokens))}")
    else:
        print("Canonical strip tokens: (none — exact-name clusters only)")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
