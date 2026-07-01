#!/usr/bin/env python3
"""Find potential duplicate Projects tenant-wide and write the standard CSV."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import endorlabs

CSV_FIELDS = ["project name", "namespace", "uuid", "source"]


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


def project_source_label(client: endorlabs.Client, row: dict[str, Any]) -> str:
    return "Cloud Scan" if client.Project.is_app(row) else "CLI"


def row_to_csv(client: endorlabs.Client, row: dict[str, Any]) -> dict[str, str]:
    return {
        "project name": project_name(row),
        "namespace": project_namespace(row),
        "uuid": row.get("uuid") or "",
        "source": project_source_label(client, row),
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


def write_csv(
    client: endorlabs.Client,
    clusters: list[list[dict[str, Any]]],
    output: Path,
) -> list[dict[str, str]]:
    rows = [row_to_csv(client, r) for cluster in clusters for r in cluster]
    rows.sort(key=lambda r: (r["project name"].lower(), r["namespace"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


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
        default=Path(
            ".endorlabs-context/workspace/sessions/agent/exports/duplicate-projects.csv"
        ),
        help="CSV output path",
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
    args = parser.parse_args()

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
    rows = write_csv(client, clusters, args.output)

    eligible = len(projects) - sbom_count
    print(
        f"Scanned {len(projects)} projects ({sbom_count} SBOM excluded, {eligible} eligible); "
        f"{len(clusters)} duplicate clusters; {len(rows)} CSV rows"
    )
    if strip_tokens:
        print(f"Canonical strip tokens: {', '.join(sorted(strip_tokens))}")
    else:
        print("Canonical strip tokens: (none — exact-name clusters only)")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
