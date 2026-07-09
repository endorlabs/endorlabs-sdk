#!/usr/bin/env python3
"""Idealized validation: ``client.Query.Project.*`` vs facade baselines.

Exercises the shipped SDK surface used by estate workflows (dashboard counts,
collect preflight, topology discovery). Writes a JSON report under
``.tmp/query_workflow_probes/results/``.

Auth (browser once, then token-only):

  uv run endor-auth refresh --env-file .env-admin --method sso -n endor-admin
  uv run --env-file .env-admin python .tmp/query_workflow_probes/validate_query_facade.py -n <tenant>

Do not invent auth env vars (e.g. ``ENDOR_AUTH_METHOD``) when running this script.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from endorlabs.filters import (
    dm_importer_project_filter,
    estate_findings_filter,
    pv_count_filter,
    to_query_filter,
)
from endorlabs.query import validate_sample

from common import ProbeResult, make_client, project_wire_namespace, write_report


def _log(msg: str) -> None:
    print(msg, flush=True)


def _project_ns(project: Any) -> str:
    ns = getattr(project, "namespace", None)
    if ns:
        return str(ns)
    return project_wire_namespace(project)


def _project_uid(project: Any) -> str:
    return str(getattr(project, "uuid", None) or project.get("uuid"))


def _facade_pv_count(client: Any, project: Any) -> int:
    uid = _project_uid(project)
    ns = _project_ns(project)
    return int(
        client.PackageVersion.count(
            namespace=ns,
            filter=pv_count_filter(uid),
        )
    )


def _facade_dm_count(client: Any, project: Any) -> int:
    uid = _project_uid(project)
    ns = _project_ns(project)
    return int(
        client.DependencyMetadata.count(
            namespace=ns,
            filter=dm_importer_project_filter(uid),
        )
    )


def _facade_finding_count(client: Any, project: Any) -> int:
    uid = _project_uid(project)
    ns = _project_ns(project)
    filt = to_query_filter(f"{estate_findings_filter()} and spec.project_uuid=={uid!r}")
    return int(client.Finding.count(namespace=ns, filter=filt, traverse=False))


def _check_discover(client: Any, namespace: str) -> ProbeResult:
    t0 = time.perf_counter()
    topo = client.Query.Project.discover(namespace, traverse=True, max_pages=1)
    elapsed = time.perf_counter() - t0
    ok = topo.project_count > 0 and bool(topo.namespace_geometry)
    return ProbeResult(
        name="discover-topology",
        elapsed_s=elapsed,
        ok=ok,
        detail={
            "tenant": topo.tenant,
            "archetype": topo.archetype,
            "project_count": topo.project_count,
            "namespace_count": topo.namespace_count,
            "shard_count": len(topo.project_shards()),
            "scope_count": len(topo.query_scopes()),
        },
    )


def _check_validate_sample(
    client: Any,
    projects: list[Any],
    *,
    recipe: str,
) -> ProbeResult:
    t0 = time.perf_counter()
    result = validate_sample(client, projects, recipe=recipe, sample_size=min(5, len(projects)))
    elapsed = time.perf_counter() - t0
    return ProbeResult(
        name=f"validate-sample-{recipe}",
        elapsed_s=elapsed,
        ok=result.matched,
        detail=result.to_dict(),
    )


def _check_count_pv(client: Any, projects: list[Any]) -> ProbeResult:
    sample = projects[: min(3, len(projects))]
    t0 = time.perf_counter()
    query_counts = client.Query.Project.count_pv(sample)
    elapsed = time.perf_counter() - t0
    mismatches: list[dict[str, Any]] = []
    for row in sample:
        uid = str(getattr(row, "uuid", None) or row.get("uuid"))
        facade = _facade_pv_count(client, row)
        query_val = int(query_counts.get(uid, -1))
        if query_val != facade:
            mismatches.append(
                {"project_uuid": uid, "query": query_val, "facade": facade}
            )
    return ProbeResult(
        name="count-pv-facade-parity",
        elapsed_s=elapsed,
        ok=not mismatches,
        detail={
            "sample_size": len(sample),
            "query_totals": {
                _project_uid(r): query_counts.get(_project_uid(r)) for r in sample
            },
            "mismatches": mismatches,
        },
    )


def _check_count_dm(client: Any, projects: list[Any]) -> ProbeResult:
    sample = projects[: min(3, len(projects))]
    t0 = time.perf_counter()
    query_counts = client.Query.Project.count_dm(sample)
    elapsed = time.perf_counter() - t0
    mismatches: list[dict[str, Any]] = []
    for row in sample:
        uid = str(getattr(row, "uuid", None) or row.get("uuid"))
        facade = _facade_dm_count(client, row)
        query_val = int(query_counts.get(uid, -1))
        if query_val != facade:
            mismatches.append(
                {"project_uuid": uid, "query": query_val, "facade": facade}
            )
    return ProbeResult(
        name="count-dm-facade-parity",
        elapsed_s=elapsed,
        ok=not mismatches,
        detail={"sample_size": len(sample), "mismatches": mismatches},
    )


def _check_count_findings(client: Any, projects: list[Any]) -> ProbeResult:
    sample = projects[: min(3, len(projects))]
    t0 = time.perf_counter()
    query_counts = client.Query.Project.count_findings_by_category(sample)
    elapsed = time.perf_counter() - t0
    mismatches: list[dict[str, Any]] = []
    for row in sample:
        uid = str(getattr(row, "uuid", None) or row.get("uuid"))
        facade_total = _facade_finding_count(client, row)
        query_total = sum(int(v) for v in (query_counts.get(uid) or {}).values())
        if query_total != facade_total:
            mismatches.append(
                {
                    "project_uuid": uid,
                    "query_total": query_total,
                    "facade_total": facade_total,
                    "query_by_category": query_counts.get(uid),
                }
            )
    return ProbeResult(
        name="count-findings-category-parity",
        elapsed_s=elapsed,
        ok=not mismatches,
        detail={"sample_size": len(sample), "mismatches": mismatches},
    )


def _check_collect_estate_findings(
    client: Any,
    projects: list[Any],
) -> ProbeResult:
    """Smoke: full collect row count vs facade Finding.count on a small sample."""
    sample = projects[: min(2, len(projects))]
    facade_total = sum(_facade_finding_count(client, row) for row in sample)
    t0 = time.perf_counter()
    rows = client.Query.Project.collect_estate_findings(
        sample,
        mask="uuid,spec.level,spec.finding_categories",
        max_root_pages=None,
    )
    elapsed = time.perf_counter() - t0
    ok = len(rows) == facade_total
    return ProbeResult(
        name="collect-estate-findings-smoke",
        elapsed_s=elapsed,
        ok=ok,
        detail={
            "sample_size": len(sample),
            "rows_returned": len(rows),
            "facade_total": facade_total,
            "row_parity": len(rows) == facade_total,
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate client.Query.Project recipes against facade baselines",
    )
    parser.add_argument("-n", "--namespace", required=True, help="Tenant root namespace")
    parser.add_argument(
        "--max-projects",
        type=int,
        default=8,
        help="Cap projects sampled from discovery",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(".tmp/query_workflow_probes/results"),
        help="Report output directory",
    )
    args = parser.parse_args(argv)

    exit_code = 0
    results: list[dict[str, Any]] = []

    with make_client(args.namespace) as client:
        discover = _check_discover(client, args.namespace)
        results.append(discover.to_dict())
        _log(f"[{'OK' if discover.ok else 'FAIL'}] {discover.name} ({discover.elapsed_s:.2f}s)")
        if not discover.ok:
            exit_code = 1

        topo = client.Query.Project.discover(args.namespace, traverse=True, max_pages=1)
        projects = topo.projects[: args.max_projects]
        if not projects:
            _log("No projects in scope — aborting recipe checks")
            return 1

        checks = [
            _check_validate_sample(client, projects, recipe="pv"),
            _check_validate_sample(client, projects, recipe="dm"),
            _check_validate_sample(client, projects, recipe="findings"),
            _check_validate_sample(client, projects, recipe="severity"),
            _check_count_pv(client, projects),
            _check_count_dm(client, projects),
            _check_collect_estate_findings(client, projects),
        ]
        for result in checks:
            results.append(result.to_dict())
            status = "OK" if result.ok else "FAIL"
            _log(f"[{status}] {result.name} ({result.elapsed_s:.2f}s)")
            if not result.ok:
                _log(f"       {result.detail}")
                exit_code = 1

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_path = args.out / f"validate_query_facade_{args.namespace.replace('.', '_')}_{stamp}.json"
    write_report(
        out_path,
        {
            "namespace": args.namespace,
            "script": "validate_query_facade.py",
            "results": results,
        },
    )
    _log(f"\nWrote {out_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
