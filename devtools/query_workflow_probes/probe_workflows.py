#!/usr/bin/env python3
"""
Probe Query.create as a replacement for workflow list/count patterns.

Auth (browser once, then token-only for probes):
  uv run endor-auth refresh --env-file .env-admin --method sso -n endor-admin
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py all -n <tenant>

Do not invent auth env vars (e.g. ENDOR_AUTH_METHOD) when running probes.
Probes reuse one Client and ENDOR_TOKEN from the dotenv file (no browser OAuth).

Usage:
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py recipe-parity -n smarsh
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py prf-counts -n smarsh --max-projects 5
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py finding-list-join -n smarsh
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py findinglog-group -n smarsh
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py dm-group -n smarsh
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py nested-list -n smarsh
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py scan-latest-join -n smarsh
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py collect-row-parity -n smarsh
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py malware-category-split -n smarsh
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py tenant-finding-totals -n smarsh
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py query-escape-hatch-group-by-time -n smarsh
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py authlog-group-by-time -n smarsh
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py nested-finding-mask -n smarsh
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py severity-validate-sample -n smarsh
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py collect-prf-rows -n smarsh
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py probe-ref-pagination-wire -n smarsh
  uv run --env-file .env-admin python .tmp/query_workflow_probes/probe_workflows.py all -n smarsh --out .tmp/query_workflow_probes/results
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from endorlabs.filters import (
    category_filter,
    estate_findings_filter,
    finding_log_time_window_filter,
    prf_vuln_filter,
    reachable_vuln_log_base_filter,
    to_query_filter,
)
from endorlabs.filters.finding_categories import FINDING_CATEGORIES
from endorlabs.query import (
    QuerySpec,
    estate_findings_list_spec,
    extract_group_response,
    extract_query_response,
    parse_query_root_count,
    validate_sample,
)
from endorlabs.query.parse import reference_list_objects

from common import (
    ProbeResult,
    discover_projects,
    extract_query_objects,
    make_client,
    parse_group_bucket_counts,
    project_wire_namespace,
    query_create,
    next_page_token,
    reference_count,
    reference_total,
    resolve_tenant,
    wire_dict,
    write_report,
)

ECOSYSTEMS = {
    "NUGET": "ECOSYSTEM_NUGET",
    "NPM": "ECOSYSTEM_NPM",
    "MAVEN": "ECOSYSTEM_MAVEN",
    "PYPI": "ECOSYSTEM_PYPI",
}

DEFAULT_ESTATE_FINDING_MASK = (
    "uuid,"
    "spec.level,"
    "spec.finding_categories,"
    "spec.target_dependency_package_name,"
    "spec.target_dependency_name,"
    "spec.target_dependency_version,"
    "spec.finding_tags"
)

MASK_PROBE_FIELDS = (
    "spec.target_dependency_package_name",
    "spec.target_dependency_name",
    "spec.target_dependency_version",
)


def _log(msg: str) -> None:
    print(msg, flush=True)


def _sample_projects(client: Any, namespace: str, cap: int) -> list[dict[str, Any]]:
    projects = discover_projects(client, namespace, cap=cap)
    if not projects:
        raise SystemExit(f"No projects under {namespace!r}")
    return projects


def _group_by_namespace(projects: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for row in projects:
        out[project_wire_namespace(row)].append(str(row["uuid"]))
    return dict(out)


def _uuid_in_filter(uuids: list[str]) -> str:
    quoted = ", ".join(f'"{uid}"' for uid in uuids)
    return f"uuid in [{quoted}]"


def _row_uuid(row: Any) -> str:
    item = wire_dict(row)
    return str(item.get("uuid") or "")


def _nested_field(row: dict[str, Any], path: str) -> Any:
    """Read a dotted path from a masked dict row."""
    cur: Any = row
    for part in path.split("."):
        cur = wire_dict(cur).get(part) if isinstance(cur, dict) else None
        if cur is None:
            return None
    return cur


def _find_project_with_findings(
    client: Any,
    namespace: str,
    *,
    scan_cap: int = 25,
    min_count: int = 1,
) -> tuple[dict[str, Any] | None, int]:
    """Return first sampled project with at least ``min_count`` estate findings."""
    filt = to_query_filter(estate_findings_filter())
    for row in discover_projects(client, namespace, cap=scan_cap):
        uid = str(row["uuid"])
        leaf_ns = project_wire_namespace(row)
        scoped = f"{filt} and spec.project_uuid=={uid!r}"
        count = int(client.Finding.count(namespace=leaf_ns, filter=scoped, traverse=False))
        if count >= min_count:
            return row, count
    return None, 0


def _group_by_time_wire(
    *,
    start: datetime,
    end: datetime,
    time_path: str = "meta.create_time",
    interval: str = "GROUP_BY_TIME_INTERVAL_DAY",
) -> dict[str, Any]:
    """Inline group_by_time list_parameters (no SDK builder — removed from public API)."""
    return {
        "aggregation_paths": time_path,
        "interval": interval,
        "mode": "count",
        "start_time": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_time": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _query_group_by_time_negative(
    client: Any,
    *,
    kind: str,
    namespace: str,
    filt: str,
    traverse: bool,
    start: datetime,
    end: datetime,
    probe_name: str,
    workflow: str,
) -> ProbeResult:
    """Assert Query returns list.objects (not group_response) for group_by_time-only specs."""
    t0 = time.perf_counter()
    query_err: str | None = None
    list_objects: list[Any] = []
    grp: dict[str, Any] = {}
    try:
        spec = {
            "kind": kind,
            "list_parameters": {
                "filter": filt,
                "traverse": traverse,
                "group_by_time": _group_by_time_wire(start=start, end=end),
            },
        }
        result = query_create(
            client,
            namespace=namespace,
            name=probe_name,
            query_spec=spec,
        )
        grp = extract_group_response(result)
        list_objects = extract_query_objects(result)
        if grp:
            query_err = "unexpected group_response — platform may have fixed routing"
            ok = False
        elif list_objects:
            query_err = (
                "platform returns list.objects instead of group_response — "
                f"Query.create does not honor group_by_time for {kind}; use list_groups"
            )
            ok = False
        else:
            query_err = "empty query_response"
            ok = False
    except Exception as exc:  # noqa: BLE001
        query_err = str(exc)
        ok = False
    elapsed = time.perf_counter() - t0
    return ProbeResult(
        name=probe_name,
        elapsed_s=elapsed,
        ok=ok,
        detail={
            "workflow": workflow,
            "root_kind": kind,
            "aggregation": "group_by_time (Query escape hatch / raw payload)",
            "filter": filt,
            "error": query_err,
            "query_list_objects": len(list_objects) if list_objects else 0,
            "has_group_response": bool(grp),
            "expected_unsupported": True,
        },
    )


def probe_recipe_parity(client: Any, namespace: str, *, cap: int) -> list[ProbeResult]:
    """Workflow: online dashboard / estate preflight — shipped count recipes."""
    topo = client.Query.Project.discover(namespace, traverse=True, max_pages=1)
    projects = topo.projects[:cap]
    if not projects:
        raise SystemExit(f"No projects under {namespace!r}")
    results: list[ProbeResult] = []
    for recipe in ("pv", "dm", "findings"):
        t0 = time.perf_counter()
        validation = validate_sample(
            client, projects, recipe=recipe, sample_size=min(5, len(projects))
        )
        elapsed = time.perf_counter() - t0
        results.append(
            ProbeResult(
                name=f"recipe-parity-{recipe}",
                elapsed_s=elapsed,
                ok=validation.matched,
                detail={
                    "workflow": "fetch_online_dashboard_counts / estate preflight",
                    "sdk_path": f"client.Query.Project.validate_sample(recipe={recipe!r})",
                    "validation": validation.to_dict(),
                },
            )
        )
    t0 = time.perf_counter()
    pv_counts = client.Query.Project.count_pv(projects[: min(3, len(projects))])
    elapsed = time.perf_counter() - t0
    results.append(
        ProbeResult(
            name="recipe-parity-count-pv",
            elapsed_s=elapsed,
            ok=isinstance(pv_counts, dict) and bool(pv_counts),
            detail={
                "sdk_path": "client.Query.Project.count_pv",
                "sample": dict(list(pv_counts.items())[:3]),
            },
        )
    )
    return results


def probe_prf_counts(client: Any, namespace: str, *, cap: int) -> list[ProbeResult]:
    """Workflow: PRF analysis — per-ecosystem PRF vuln totals."""
    projects = _sample_projects(client, namespace, cap)
    base = prf_vuln_filter()
    by_ns = _group_by_namespace(projects)

    # Facade: sum Finding.count per project × ecosystem
    facade_totals: dict[str, int] = {eco: 0 for eco in ECOSYSTEMS}
    t0 = time.perf_counter()
    for row in projects:
        ns = project_wire_namespace(row)
        uid = str(row["uuid"])
        for eco_label, eco_enum in ECOSYSTEMS.items():
            filt = f"{base} and spec.ecosystem=={eco_enum} and spec.project_uuid=={uid}"
            facade_totals[eco_label] += int(
                client.Finding.count(namespace=ns, filter=filt, traverse=False)
            )
    facade_elapsed = time.perf_counter() - t0

    # Query: one POST per leaf NS, four Finding count refs (return_as per ecosystem)
    query_totals: dict[str, int] = {eco: 0 for eco in ECOSYSTEMS}
    t0 = time.perf_counter()
    for ns, uuids in by_ns.items():
        references = []
        for eco_label, eco_enum in ECOSYSTEMS.items():
            references.append(
                {
                    "connect_from": "uuid",
                    "connect_to": "spec.project_uuid",
                    "query_spec": {
                        "return_as": f"Prf{eco_label}Count",
                        "kind": "Finding",
                        "list_parameters": {
                            "count": True,
                            "filter": f"{base} and spec.ecosystem=={eco_enum}",
                        },
                    },
                }
            )
        spec = {
            "kind": "Project",
            "list_parameters": {
                "mask": "uuid,meta.name",
                "traverse": False,
                "filter": _uuid_in_filter(uuids),
            },
            "references": references,
        }
        result = query_create(
            client, namespace=ns, name="probe-prf-ecosystem-counts", query_spec=spec
        )
        for obj in extract_query_objects(result):
            for eco_label in ECOSYSTEMS:
                query_totals[eco_label] += reference_count(obj, f"Prf{eco_label}Count")
    query_elapsed = time.perf_counter() - t0
    match = facade_totals == query_totals

    return [
        ProbeResult(
            name="prf-ecosystem-counts-facade",
            elapsed_s=facade_elapsed,
            ok=True,
            detail={"totals": facade_totals, "api_calls": len(projects) * len(ECOSYSTEMS)},
        ),
        ProbeResult(
            name="prf-ecosystem-counts-query",
            elapsed_s=query_elapsed,
            ok=match,
            detail={
                "workflow": "endor-potentially-reachable-analysis (aggregate step)",
                "root_kind": "Project",
                "joins": ["Project.uuid -> Finding.spec.project_uuid"] * 4,
                "aggregation": "count per ecosystem ref (return_as)",
                "filter": base,
                "totals": query_totals,
                "facade_totals": facade_totals,
                "match": match,
                "api_calls": len(by_ns),
            },
        ),
    ]


def probe_finding_list_join(client: Any, namespace: str, *, cap: int) -> list[ProbeResult]:
    """Workflow: estate findings collect — compare count refs (list parity for totals)."""
    projects = _sample_projects(client, namespace, min(cap, 2))
    filt = to_query_filter(estate_findings_filter())

    facade_totals: dict[str, int] = {}
    t0 = time.perf_counter()
    for row in projects:
        uid = str(row["uuid"])
        ns = project_wire_namespace(row)
        scoped = f"{filt} and spec.project_uuid=={uid}"
        facade_totals[uid] = int(
            client.Finding.count(namespace=ns, filter=scoped, traverse=False)
        )
    facade_elapsed = time.perf_counter() - t0

    query_totals: dict[str, int | None] = {}
    query_page_tokens: dict[str, int | None] = {}
    t0 = time.perf_counter()
    for row in projects:
        uid = str(row["uuid"])
        ns = project_wire_namespace(row)
        spec = {
            "kind": "Project",
            "list_parameters": {
                "mask": "uuid,meta.name",
                "traverse": False,
                "filter": _uuid_in_filter([uid]),
            },
            "references": [
                {
                    "connect_from": "uuid",
                    "connect_to": "spec.project_uuid",
                    "query_spec": {
                        "kind": "Finding",
                        "list_parameters": {
                            "count": True,
                            "filter": filt,
                        },
                    },
                }
            ],
        }
        result = query_create(
            client, namespace=ns, name="probe-finding-count-join", query_spec=spec
        )
        query_page_tokens[uid] = next_page_token(result)
        objs = extract_query_objects(result)
        if not objs:
            query_totals[uid] = 0
            continue
        query_totals[uid] = reference_total(objs[0], "Finding")
    query_elapsed = time.perf_counter() - t0
    match = all(query_totals.get(uid) == facade_totals.get(uid) for uid in facade_totals)

    return [
        ProbeResult(
            name="finding-list-join-facade",
            elapsed_s=facade_elapsed,
            ok=True,
            detail={"per_project_total": facade_totals, "method": "Finding.count"},
        ),
        ProbeResult(
            name="finding-list-join-query",
            elapsed_s=query_elapsed,
            ok=match,
            detail={
                "workflow": "endor-estate pull findings collect",
                "root_kind": "Project",
                "joins": ["Project.uuid -> Finding.spec.project_uuid"],
                "aggregation": "count ref on Finding (parity with Finding.count)",
                "filter": filt,
                "per_project_total": query_totals,
                "facade_totals": facade_totals,
                "root_next_page_token": query_page_tokens,
                "match": match,
                "pagination_note": (
                    "Totals use count refs. Masked list rows paginate via nested "
                    "reference list.response.next_page_token (collect_* / QueryExecutor)."
                ),
            },
        ),
    ]


def probe_findinglog_group(
    client: Any, namespace: str, *, findinglog_days: int = 7
) -> list[ProbeResult]:
    """Workflow: chart new-vs-resolved — FindingLog group_by_time (scoped window)."""
    tenant = resolve_tenant(namespace)
    end = datetime.now(UTC).replace(microsecond=0)
    start = end - timedelta(days=findinglog_days)
    base = reachable_vuln_log_base_filter()
    time_filt = finding_log_time_window_filter(start, end, base_filter=base)
    filt = to_query_filter(
        f"{time_filt} and spec.operation==OPERATION_CREATE "
        "and spec.level in [FINDING_LEVEL_CRITICAL, FINDING_LEVEL_HIGH]"
    )
    window_label = f"{start.isoformat()} .. {end.isoformat()} ({findinglog_days}d)"

    # Facade path (today) — same filter window as Query
    from endorlabs.workflows.logs.group_by_time import group_by_time_counts

    t0 = time.perf_counter()
    try:
        facade_buckets = group_by_time_counts(
            client.FindingLog.list_groups,
            namespace=tenant,
            filter=filt,
            traverse=True,
            interval="day",
        )
        facade_ok = True
        facade_err = None
    except Exception as exc:  # noqa: BLE001
        facade_buckets = {}
        facade_ok = False
        facade_err = str(exc)
    facade_elapsed = time.perf_counter() - t0

    # Query path: root FindingLog with group_by_time in list_parameters
    t0 = time.perf_counter()
    query_ok = False
    query_err: str | None = None
    query_buckets: dict[str, int] = {}
    facade_match = False
    list_objects: list[Any] = []
    grp: dict[str, Any] = {}
    try:
        spec = {
            "kind": "FindingLog",
            "list_parameters": {
                "filter": filt,
                "traverse": True,
                "group_by_time": {
                    "aggregation_paths": "meta.create_time",
                    "interval": "GROUP_BY_TIME_INTERVAL_DAY",
                    "mode": "count",
                    "start_time": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "end_time": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            },
        }
        result = query_create(
            client,
            namespace=tenant,
            name="probe-findinglog-group-by-time",
            query_spec=spec,
        )
        qr = extract_query_response(result)
        grp = extract_group_response(result)
        list_objects = extract_query_objects(result)
        query_buckets = parse_group_bucket_counts(result)
        if grp:
            query_ok = bool(query_buckets)
            facade_match = query_buckets == facade_buckets if facade_ok else False
            if not query_ok:
                query_err = "empty group_response"
            elif not facade_match and facade_ok:
                query_err = "bucket mismatch vs facade"
                query_ok = False
        elif list_objects:
            query_err = (
                "platform returns list.objects instead of group_response — "
                "Query.create does not honor group_by_time for FindingLog; "
                "use FindingLog.list_groups"
            )
            query_ok = False
        else:
            query_err = "empty query_response"
            facade_match = False
    except Exception as exc:  # noqa: BLE001
        query_err = str(exc)
    query_elapsed = time.perf_counter() - t0

    findinglog_query_detail = {
                "workflow": "endor-chart-new-vs-resolved-findings",
                "root_kind": "FindingLog",
                "joins": [],
                "aggregation": "group_by_time on meta.create_time (day)",
                "filter": time_filt,
                "window": window_label,
                "bucket_count": len(query_buckets),
                "sample_buckets": dict(list(query_buckets.items())[:3]),
                "error": query_err,
                "facade_bucket_count": len(facade_buckets),
                "facade_match": facade_match if facade_ok else None,
                "query_list_objects": len(list_objects) if list_objects else 0,
                "has_group_response": bool(grp),
            }
    if not query_ok and list_objects and not grp:
        findinglog_query_detail["expected_unsupported"] = True

    return [
        ProbeResult(
            name="findinglog-group-facade",
            elapsed_s=facade_elapsed,
            ok=facade_ok,
            detail={
                "window": window_label,
                "bucket_count": len(facade_buckets),
                "sample_buckets": dict(list(facade_buckets.items())[:3]),
                "error": facade_err,
            },
        ),
        ProbeResult(
            name="findinglog-group-query",
            elapsed_s=query_elapsed,
            ok=query_ok,
            detail=findinglog_query_detail,
        ),
    ]


def _find_dm_sample_project(
    client: Any,
    namespace: str,
    *,
    scan_cap: int = 20,
) -> tuple[dict[str, Any] | None, list[Any]]:
    """Return first project row with DM group buckets, or (None, scanned rows)."""
    from endorlabs.filters import MAIN_CONTEXT_LIST_FILTER, to_query_filter

    from endorlabs.workflows.estate.analyze.cardinality.columns import (
        PACKAGE_NAME_PATH,
        PACKAGE_VERSION_PATH,
    )

    dm_group_paths = [PACKAGE_NAME_PATH, PACKAGE_VERSION_PATH]
    projects = discover_projects(client, namespace, cap=scan_cap)
    for row in projects:
        uid = str(row["uuid"])
        leaf_ns = project_wire_namespace(row)
        filt = to_query_filter(
            f'{MAIN_CONTEXT_LIST_FILTER} and spec.importer_data.project_uuid=="{uid}"'
        )
        facade_groups = list(
            client.DependencyMetadata.list_groups(
                namespace=leaf_ns,
                traverse=False,
                filter=filt,
                group_aggregation_paths=dm_group_paths,
                max_pages=1,
            )
        )
        if facade_groups:
            return row, facade_groups
    return None, projects


def probe_dm_group(client: Any, namespace: str, *, cap: int = 1) -> list[ProbeResult]:
    """Workflow: DM version cardinality — scoped to one importer project."""
    from endorlabs.filters import MAIN_CONTEXT_LIST_FILTER, to_query_filter

    from endorlabs.workflows.estate.analyze.cardinality.columns import (
        PACKAGE_NAME_PATH,
        PACKAGE_VERSION_PATH,
    )

    dm_group_paths = [PACKAGE_NAME_PATH, PACKAGE_VERSION_PATH]
    project, preset_groups = _find_dm_sample_project(
        client, namespace, scan_cap=max(cap, 20)
    )
    if project is None:
        return [
            ProbeResult(
                name="dm-group-facade",
                elapsed_s=0.0,
                ok=True,
                detail={
                    "note": f"No DM group buckets in first {max(cap, 20)} projects",
                    "group_buckets": 0,
                },
            ),
            ProbeResult(
                name="dm-group-query",
                elapsed_s=0.0,
                ok=True,
                detail={
                    "note": "Skipped — no importer DM rows to compare",
                    "group_buckets": 0,
                    "facade_group_buckets": 0,
                    "match": True,
                },
            ),
        ]

    project_uuid = str(project["uuid"])
    leaf_ns = project_wire_namespace(project)
    filt = to_query_filter(
        f'{MAIN_CONTEXT_LIST_FILTER} and spec.importer_data.project_uuid=="{project_uuid}"'
    )

    t0 = time.perf_counter()
    try:
        facade_groups = preset_groups or list(
            client.DependencyMetadata.list_groups(
                namespace=leaf_ns,
                traverse=False,
                filter=filt,
                group_aggregation_paths=dm_group_paths,
                max_pages=1,
            )
        )
        facade_ok = True
        facade_err = None
    except Exception as exc:  # noqa: BLE001
        facade_groups = []
        facade_ok = False
        facade_err = str(exc)
    facade_elapsed = time.perf_counter() - t0

    t0 = time.perf_counter()
    query_ok = False
    query_err: str | None = None
    query_group_count = 0
    try:
        spec = {
            "kind": "DependencyMetadata",
            "list_parameters": {
                "filter": filt,
                "traverse": False,
                "group": {
                    "aggregation_paths": ",".join(dm_group_paths),
                },
            },
        }
        result = query_create(
            client,
            namespace=leaf_ns,
            name="probe-dm-version-group",
            query_spec=spec,
        )
        from endorlabs.query import iter_group_buckets

        query_group_count = sum(1 for _ in iter_group_buckets(result))
        query_ok = True
        if facade_groups and query_group_count == 0:
            query_err = "empty group_response"
            query_ok = False
    except Exception as exc:  # noqa: BLE001
        query_err = str(exc)
    query_elapsed = time.perf_counter() - t0
    group_match = query_group_count == len(facade_groups)

    return [
        ProbeResult(
            name="dm-group-facade",
            elapsed_s=facade_elapsed,
            ok=facade_ok,
            detail={
                "scope": {"project_uuid": project_uuid, "namespace": leaf_ns},
                "group_buckets": len(facade_groups),
                "error": facade_err,
            },
        ),
        ProbeResult(
            name="dm-group-query",
            elapsed_s=query_elapsed,
            ok=query_ok and group_match,
            detail={
                "workflow": "estate analyze DM version cardinality",
                "root_kind": "DependencyMetadata",
                "joins": [],
                "aggregation": f"group on {','.join(dm_group_paths)}",
                "filter": filt,
                "scope": {"project_uuid": project_uuid, "namespace": leaf_ns},
                "group_buckets": query_group_count,
                "facade_group_buckets": len(facade_groups),
                "match": group_match,
                "error": query_err,
            },
        ),
    ]


SCAN_FACADE_MASK = (
    "spec.environment.config.RunBySystem,"
    "spec.environment.endorctl_version,"
    "meta.create_time"
)
# Query list refs do not populate sub-fields under struct masks (e.g.
# config.RunBySystem alone → empty config). Mask the parent struct instead.
SCAN_QUERY_MASK = "spec.environment,meta.create_time"


def _scan_fingerprint(row: dict[str, Any] | None) -> tuple[str | None, bool | None, str | None]:
    """Normalize latest-scan fields for facade vs Query parity."""
    if not row:
        return (None, None, None)
    spec = wire_dict(row.get("spec"))
    environment = wire_dict(spec.get("environment"))
    config = wire_dict(environment.get("config"))
    meta = wire_dict(row.get("meta"))
    run_by = config.get("RunBySystem")
    run_by_bool = bool(run_by) if run_by is not None else None
    version = environment.get("endorctl_version")
    version_str = str(version) if version is not None else None
    create_time = meta.get("create_time")
    create_str = str(create_time) if create_time is not None else None
    return (version_str, run_by_bool, create_str)


def probe_scan_latest_join(client: Any, namespace: str, *, cap: int) -> list[ProbeResult]:
    """Workflow: CI endorctl audit / inventory — latest ScanResult per project."""
    projects = _sample_projects(client, namespace, cap)
    by_ns = _group_by_namespace(projects)

    facade_fps: dict[str, tuple[str | None, bool | None, str | None]] = {}
    t0 = time.perf_counter()
    for row in projects:
        uid = str(row["uuid"])
        ns = project_wire_namespace(row)
        scans = client.ScanResult.list_by_project(
            row,
            namespace=ns,
            mask=SCAN_FACADE_MASK,
            limit=1,
        )
        scan_row = wire_dict(scans[0]) if scans else None
        facade_fps[uid] = _scan_fingerprint(scan_row)
    facade_elapsed = time.perf_counter() - t0

    query_fps: dict[str, tuple[str | None, bool | None, str | None]] = {}
    query_err: str | None = None
    t0 = time.perf_counter()
    try:
        for ns, uuids in by_ns.items():
            spec = {
                "kind": "Project",
                "list_parameters": {
                    "mask": "uuid,meta.name",
                    "traverse": False,
                    "filter": _uuid_in_filter(uuids),
                },
                "references": [
                    {
                        "connect_from": "uuid",
                        "connect_to": "meta.parent_uuid",
                        "query_spec": {
                            "kind": "ScanResult",
                            "list_parameters": {
                                "mask": SCAN_QUERY_MASK,
                                "page_size": 1,
                                "sort": {
                                    "path": "meta.create_time",
                                    "order": "SORT_ENTRY_ORDER_DESC",
                                },
                            },
                        },
                    }
                ],
            }
            result = query_create(
                client, namespace=ns, name="probe-scan-latest-join", query_spec=spec
            )
            for obj in extract_query_objects(result):
                uid = str(obj.get("uuid") or "")
                scans = reference_list_objects(obj, "ScanResult")
                query_fps[uid] = _scan_fingerprint(scans[0] if scans else None)
    except Exception as exc:  # noqa: BLE001
        query_err = str(exc)
    query_elapsed = time.perf_counter() - t0

    mismatches = {
        uid: {"facade": facade_fps.get(uid), "query": query_fps.get(uid)}
        for uid in facade_fps
        if facade_fps.get(uid) != query_fps.get(uid)
    }
    match = not mismatches and query_err is None

    return [
        ProbeResult(
            name="scan-latest-join-facade",
            elapsed_s=facade_elapsed,
            ok=True,
            detail={
                "workflow": "endor-ci-endorctl-version-audit / projects.inventory",
                "method": "ScanResult.list_by_project(limit=1) per project",
                "api_calls": len(projects),
                "sample": dict(list(facade_fps.items())[:3]),
            },
        ),
        ProbeResult(
            name="scan-latest-join-query",
            elapsed_s=query_elapsed,
            ok=match,
            detail={
                "workflow": "endor-ci-endorctl-version-audit / projects.inventory",
                "root_kind": "Project",
                "joins": ["Project.uuid -> ScanResult.meta.parent_uuid"],
                "aggregation": "masked list, newest first, page_size=1",
                "api_calls": len(by_ns),
                "match": match,
                "mismatches": mismatches,
                "error": query_err,
                "sample": dict(list(query_fps.items())[:3]),
                "note": (
                    "Query list refs: mask parent struct spec.environment "
                    "(sub-field masks return empty config)."
                ),
            },
        ),
    ]


def probe_nested_list(client: Any, namespace: str, *, cap: int) -> list[ProbeResult]:
    """Platform doc pattern: Project -> RepositoryVersion -> Metric masked lists."""
    projects = _sample_projects(client, namespace, min(cap, 2))
    row = projects[0]
    ns = project_wire_namespace(row)
    uid = str(row["uuid"])

    spec = {
        "kind": "Project",
        "list_parameters": {
            "mask": "uuid,meta.name",
            "traverse": False,
            "filter": _uuid_in_filter([uid]),
        },
        "references": [
            {
                "connect_from": "uuid",
                "connect_to": "meta.parent_uuid",
                "query_spec": {
                    "kind": "RepositoryVersion",
                    "list_parameters": {
                        "filter": "context.type==CONTEXT_TYPE_MAIN",
                        "mask": "uuid,meta.name",
                    },
                    "references": [
                        {
                            "connect_from": "uuid",
                            "connect_to": "meta.parent_uuid",
                            "query_spec": {
                                "kind": "Metric",
                                "list_parameters": {
                                    "filter": 'spec.analytic=="version_cicd_tools"',
                                    "mask": "meta,spec",
                                },
                            },
                        }
                    ],
                },
            }
        ],
    }
    t0 = time.perf_counter()
    try:
        result = query_create(
            client, namespace=ns, name="probe-nested-list", query_spec=spec
        )
        objs = extract_query_objects(result)
        rv_count = 0
        metric_count = 0
        if objs:
            refs = wire_dict(wire_dict(objs[0].get("meta")).get("references"))
            rv = wire_dict(refs.get("RepositoryVersion"))
            rv_list = wire_dict(rv.get("list"))
            rv_objs = rv_list.get("objects")
            if isinstance(rv_objs, list):
                rv_count = len(rv_objs)
                for rv_obj in rv_objs:
                    rv_refs = wire_dict(wire_dict(rv_obj).get("meta")).get("references")
                    metric = wire_dict(wire_dict(rv_refs).get("Metric"))
                    m_list = wire_dict(metric.get("list"))
                    m_objs = m_list.get("objects")
                    if isinstance(m_objs, list):
                        metric_count += len(m_objs)
        ok = True
        err = None
        detail = {"repository_versions": rv_count, "metrics": metric_count}
    except Exception as exc:  # noqa: BLE001
        ok = False
        err = str(exc)
        detail = {"error": err}
    elapsed = time.perf_counter() - t0

    return [
        ProbeResult(
            name="nested-list-query",
            elapsed_s=elapsed,
            ok=ok,
            detail={
                "workflow": "platform query-service doc (RV + Metric join)",
                "root_kind": "Project",
                "joins": [
                    "Project.uuid -> RepositoryVersion.meta.parent_uuid",
                    "RepositoryVersion.uuid -> Metric.meta.parent_uuid",
                ],
                "aggregation": "masked nested lists",
                **detail,
            },
        )
    ]


def probe_collect_row_parity(client: Any, namespace: str, *, cap: int) -> list[ProbeResult]:
    """Workflow: estate findings collect — row count and uuid parity vs facade list."""
    project, facade_total = _find_project_with_findings(client, namespace, scan_cap=max(cap, 25))
    if project is None:
        return [
            ProbeResult(
                name="collect-row-parity",
                elapsed_s=0.0,
                ok=True,
                detail={"note": "No estate findings in sample — skipped", "skipped": True},
            )
        ]

    uid = str(project["uuid"])
    leaf_ns = project_wire_namespace(project)
    filt = to_query_filter(estate_findings_filter())
    scoped = f"{filt} and spec.project_uuid=={uid!r}"
    mask = DEFAULT_ESTATE_FINDING_MASK

    t0 = time.perf_counter()
    facade_rows = client.Finding.list(
        namespace=leaf_ns,
        filter=scoped,
        mask=mask,
        traverse=False,
    )
    facade_uuids = {_row_uuid(row) for row in facade_rows if _row_uuid(row)}
    facade_elapsed = time.perf_counter() - t0

    t0 = time.perf_counter()
    query_rows = client.Query.Project.collect_estate_findings(
        [project],
        mask=mask,
    )
    query_uuids = {_row_uuid(row) for row in query_rows if _row_uuid(row)}
    query_elapsed = time.perf_counter() - t0

    count_match = len(query_rows) == len(facade_rows)
    uuid_match = query_uuids == facade_uuids
    only_facade = sorted(facade_uuids - query_uuids)[:5]
    only_query = sorted(query_uuids - facade_uuids)[:5]

    return [
        ProbeResult(
            name="collect-row-parity-facade",
            elapsed_s=facade_elapsed,
            ok=True,
            detail={
                "workflow": "endor-estate pull / query_collect",
                "project_uuid": uid,
                "namespace": leaf_ns,
                "row_count": len(facade_rows),
                "facade_total_count": facade_total,
            },
        ),
        ProbeResult(
            name="collect-row-parity-query",
            elapsed_s=query_elapsed,
            ok=count_match and uuid_match,
            detail={
                "workflow": "client.Query.Project.collect_estate_findings",
                "row_count": len(query_rows),
                "facade_row_count": len(facade_rows),
                "facade_total_count": facade_total,
                "count_match": count_match,
                "uuid_match": uuid_match,
                "only_in_facade_sample": only_facade,
                "only_in_query_sample": only_query,
                "pagination_note": (
                    "Full export: nested Finding reference page_token pagination "
                    "via Query.create re-POST (probe-ref-pagination-wire)."
                ),
            },
        ),
    ]


def _reference_list_response_meta(
    project_obj: dict[str, Any], ref_key: str
) -> dict[str, Any]:
    """Read ``list.response`` metadata from a nested reference block."""
    meta = wire_dict(project_obj.get("meta"))
    refs = wire_dict(meta.get("references"))
    block = wire_dict(refs.get(ref_key))
    lst = wire_dict(block.get("list"))
    resp = wire_dict(lst.get("response"))
    objects = lst.get("objects")
    page_size = len(objects) if isinstance(objects, list) else 0
    return {
        "total": resp.get("total"),
        "next_page_token": resp.get("next_page_token"),
        "next_page_id": resp.get("next_page_id"),
        "page_size": page_size,
    }


def _inject_reference_page_token(
    wire: dict[str, Any],
    ref_key: str,
    page_token: Any,
) -> dict[str, Any]:
    """Deep-copy wire and set ``page_token`` on the matching reference list_parameters."""
    import copy

    spec = copy.deepcopy(wire)
    for ref in spec.get("references") or []:
        child = wire_dict(ref.get("query_spec"))
        kind = child.get("kind")
        return_as = child.get("return_as")
        if ref_key not in (kind, return_as):
            continue
        lp = dict(child.get("list_parameters") or {})
        lp["page_token"] = page_token
        child["list_parameters"] = lp
        ref["query_spec"] = child
        break
    return spec


def probe_ref_pagination_wire(
    client: Any, namespace: str, *, cap: int
) -> list[ProbeResult]:
    """Phase 0: probe nested Finding reference list pagination on Query.create."""
    project, facade_total = _find_project_with_findings(
        client, namespace, scan_cap=max(cap, 50), min_count=101
    )
    if project is None:
        return [
            ProbeResult(
                name="probe-ref-pagination-wire",
                elapsed_s=0.0,
                ok=True,
                detail={
                    "note": "No project with >100 estate findings in sample — skipped",
                    "skipped": True,
                },
            )
        ]

    uid = str(project["uuid"])
    leaf_ns = project_wire_namespace(project)
    base_spec = estate_findings_list_spec().for_scope_batch((uid,))

    t0 = time.perf_counter()
    page1 = query_create(
        client,
        namespace=leaf_ns,
        name="probe-ref-pagination-p1",
        query_spec=base_spec,
    )
    page1_elapsed = time.perf_counter() - t0

    objs = extract_query_objects(page1)
    if not objs:
        return [
            ProbeResult(
                name="probe-ref-pagination-wire",
                elapsed_s=page1_elapsed,
                ok=False,
                detail={"error": "empty root objects on page 1", "project_uuid": uid},
            )
        ]

    ref_meta = _reference_list_response_meta(objs[0], "Finding")
    page1_rows = reference_list_objects(objs[0], "Finding")
    ref_token = ref_meta.get("next_page_token")
    root_token = next_page_token(page1)

    ref_page2_rows: list[dict[str, Any]] = []
    ref_page2_meta: dict[str, Any] = {}
    ref_page2_elapsed = 0.0
    ref_pagination_ok = False

    if ref_token is not None:
        t0 = time.perf_counter()
        ref_spec = _inject_reference_page_token(base_spec, "Finding", ref_token)
        page2 = query_create(
            client,
            namespace=leaf_ns,
            name="probe-ref-pagination-ref-p2",
            query_spec=ref_spec,
        )
        ref_page2_elapsed = time.perf_counter() - t0
        objs2 = extract_query_objects(page2)
        if objs2:
            ref_page2_meta = _reference_list_response_meta(objs2[0], "Finding")
            ref_page2_rows = reference_list_objects(objs2[0], "Finding")
            ref_pagination_ok = len(ref_page2_rows) > 0

    root_page2_rows: list[dict[str, Any]] = []
    root_page2_meta: dict[str, Any] = {}
    root_fallback_elapsed = 0.0
    root_fallback_ok = False

    if ref_token is not None and not ref_pagination_ok and root_token is not None:
        t0 = time.perf_counter()
        root_spec = dict(base_spec)
        lp = dict(root_spec.get("list_parameters") or {})
        lp["page_token"] = root_token
        root_spec["list_parameters"] = lp
        root_page2 = query_create(
            client,
            namespace=leaf_ns,
            name="probe-ref-pagination-root-p2",
            query_spec=root_spec,
        )
        root_fallback_elapsed = time.perf_counter() - t0
        objs_root = extract_query_objects(root_page2)
        if objs_root:
            root_page2_meta = _reference_list_response_meta(objs_root[0], "Finding")
            root_page2_rows = reference_list_objects(objs_root[0], "Finding")
            root_fallback_ok = len(root_page2_rows) > 0

    combined_ref_rows = len(page1_rows) + len(ref_page2_rows)
    decision = "query_native_ref_pagination"
    if ref_token is None:
        decision = "no_ref_token_single_page"
    elif not ref_pagination_ok and root_fallback_ok:
        decision = "hybrid_root_token_fallback"
    elif not ref_pagination_ok:
        decision = "unsupported_or_needs_investigation"

    return [
        ProbeResult(
            name="probe-ref-pagination-wire",
            elapsed_s=page1_elapsed + ref_page2_elapsed + root_fallback_elapsed,
            ok=ref_token is None or ref_pagination_ok or root_fallback_ok,
            detail={
                "workflow": "Query.create nested Finding list reference pagination",
                "project_uuid": uid,
                "namespace": leaf_ns,
                "facade_total": facade_total,
                "page1": {
                    "root_next_page_token": root_token,
                    "reference_meta": ref_meta,
                    "row_count": len(page1_rows),
                },
                "ref_page2": {
                    "page_token_used": ref_token,
                    "reference_meta": ref_page2_meta,
                    "row_count": len(ref_page2_rows),
                    "ok": ref_pagination_ok,
                    "elapsed_s": ref_page2_elapsed,
                },
                "root_fallback_page2": {
                    "page_token_used": root_token,
                    "reference_meta": root_page2_meta,
                    "row_count": len(root_page2_rows),
                    "ok": root_fallback_ok,
                    "elapsed_s": root_fallback_elapsed,
                },
                "combined_ref_pages_row_count": combined_ref_rows,
                "decision": decision,
            },
        ),
    ]


def probe_collect_prf_rows(client: Any, namespace: str, *, cap: int) -> list[ProbeResult]:
    """Workflow: PRF collect — row parity vs per-ecosystem facade lists."""
    base = prf_vuln_filter()
    project: dict[str, Any] | None = None
    for row in discover_projects(client, namespace, cap=max(cap, 25)):
        uid = str(row["uuid"])
        leaf_ns = project_wire_namespace(row)
        total = 0
        for eco_enum in ECOSYSTEMS.values():
            filt = f"{base} and spec.ecosystem=={eco_enum} and spec.project_uuid=={uid}"
            total += int(client.Finding.count(namespace=leaf_ns, filter=filt, traverse=False))
        if total > 0:
            project = row
            break

    if project is None:
        return [
            ProbeResult(
                name="collect-prf-rows",
                elapsed_s=0.0,
                ok=True,
                detail={"note": "No PRF findings in sample — skipped", "skipped": True},
            )
        ]

    uid = str(project["uuid"])
    leaf_ns = project_wire_namespace(project)
    mask = (
        "uuid,spec.level,spec.finding_categories,spec.target_dependency_package_name,"
        "spec.ecosystem"
    )

    t0 = time.perf_counter()
    facade_rows: list[Any] = []
    for eco_enum in ECOSYSTEMS.values():
        filt = f"{base} and spec.ecosystem=={eco_enum}"
        facade_rows.extend(
            client.Finding.list_by_project(
                project,
                filter=filt,
                mask=mask,
            )
        )
    facade_uuids = {_row_uuid(row) for row in facade_rows if _row_uuid(row)}
    facade_elapsed = time.perf_counter() - t0

    t0 = time.perf_counter()
    query_rows = client.Query.Project.collect_prf_findings(
        [project],
        mask=mask,
    )
    query_uuids = {_row_uuid(row) for row in query_rows if _row_uuid(row)}
    query_elapsed = time.perf_counter() - t0

    count_match = len(query_rows) == len(facade_rows)
    uuid_match = query_uuids == facade_uuids

    return [
        ProbeResult(
            name="collect-prf-rows-facade",
            elapsed_s=facade_elapsed,
            ok=True,
            detail={
                "workflow": "endor-potentially-reachable-analysis collect",
                "project_uuid": uid,
                "row_count": len(facade_rows),
            },
        ),
        ProbeResult(
            name="collect-prf-rows-query",
            elapsed_s=query_elapsed,
            ok=count_match and uuid_match,
            detail={
                "workflow": "client.Query.Project.collect_prf_findings",
                "row_count": len(query_rows),
                "facade_row_count": len(facade_rows),
                "count_match": count_match,
                "uuid_match": uuid_match,
            },
        ),
    ]


def probe_malware_category_split(client: Any, namespace: str, *, cap: int) -> list[ProbeResult]:
    """Workflow: dashboard category counts — MALWARE ref vs facade (CI skips malware-only)."""
    projects = _sample_projects(client, namespace, cap)
    malware_enum = FINDING_CATEGORIES["MALWARE"]
    mismatches: list[dict[str, Any]] = []

    t0 = time.perf_counter()
    query_by_project = client.Query.Project.count_findings_by_category(projects)
    query_elapsed = time.perf_counter() - t0

    t0 = time.perf_counter()
    for row in projects:
        uid = str(row["uuid"])
        leaf_ns = project_wire_namespace(row)
        facade_malware = int(
            client.Finding.count(
                namespace=leaf_ns,
                filter=category_filter(malware_enum) + f' and spec.project_uuid=="{uid}"',
                traverse=False,
            )
        )
        query_malware = int((query_by_project.get(uid) or {}).get("MALWARE", -1))
        if query_malware != facade_malware:
            mismatches.append(
                {
                    "project_uuid": uid,
                    "query": query_malware,
                    "facade": facade_malware,
                }
            )
    facade_elapsed = time.perf_counter() - t0

    return [
        ProbeResult(
            name="malware-category-split",
            elapsed_s=query_elapsed + facade_elapsed,
            ok=not mismatches,
            detail={
                "workflow": "fetch_online_dashboard_counts (MALWARE category)",
                "sample_size": len(projects),
                "mismatches": mismatches,
                "note": "Integration tests may skip malware-only mismatches — this probe does not",
            },
        )
    ]


def probe_severity_validate_sample(client: Any, namespace: str, *, cap: int) -> list[ProbeResult]:
    """Workflow: severity dashboard — validate_sample(recipe=severity) vs facade."""
    topo = client.Query.Project.discover(namespace, traverse=True, max_pages=1)
    projects = topo.projects[:cap]
    if not projects:
        raise SystemExit(f"No projects under {namespace!r}")
    t0 = time.perf_counter()
    validation = validate_sample(
        client, projects, recipe="severity", sample_size=min(5, len(projects))
    )
    elapsed = time.perf_counter() - t0
    return [
        ProbeResult(
            name="severity-validate-sample",
            elapsed_s=elapsed,
            ok=validation.matched,
            detail={
                "workflow": "dashboard severity counts",
                "sdk_path": "client.Query.Project.validate_sample(recipe='severity')",
                "validation": validation.to_dict(),
            },
        )
    ]


def probe_tenant_finding_totals(client: Any, namespace: str, *, cap: int) -> list[ProbeResult]:
    """Workflow: tenant-wide finding totals — namespace + traverse traps."""
    tenant = resolve_tenant(namespace)
    projects = _sample_projects(client, namespace, min(cap, 3))
    filt = to_query_filter(estate_findings_filter())

    t0 = time.perf_counter()
    per_project: list[dict[str, Any]] = []
    per_project_sum = 0
    for row in projects:
        uid = str(row["uuid"])
        leaf_ns = project_wire_namespace(row)
        scoped = f"{filt} and spec.project_uuid=={uid!r}"
        facade_count = int(
            client.Finding.count(namespace=leaf_ns, filter=scoped, traverse=False)
        )
        per_project_sum += facade_count
        per_project.append(
            {
                "project_uuid": uid,
                "namespace": leaf_ns,
                "facade_count": facade_count,
            }
        )
    sample_elapsed = time.perf_counter() - t0

    t0 = time.perf_counter()
    facade_traverse_total = int(
        client.Finding.count(namespace=tenant, filter=filt, traverse=True)
    )
    traverse_elapsed = time.perf_counter() - t0

    def _query_root_count(
        post_ns: str,
        *,
        traverse: bool,
        filter_expr: str | None = None,
    ) -> int:
        spec = {
            "kind": "Finding",
            "list_parameters": {
                "count": True,
                "filter": filter_expr or filt,
                "traverse": traverse,
            },
        }
        result = query_create(
            client,
            namespace=post_ns,
            name="probe-tenant-finding-count",
            query_spec=spec,
        )
        return parse_query_root_count(result)

    t0 = time.perf_counter()
    query_err: str | None = None
    try:
        for entry in per_project:
            scoped = f"{filt} and spec.project_uuid=={entry['project_uuid']!r}"
            entry["query_count"] = _query_root_count(
                entry["namespace"],
                traverse=False,
                filter_expr=scoped,
            )
        query_tenant_no_traverse = _query_root_count(tenant, traverse=False)
        query_tenant_traverse = _query_root_count(tenant, traverse=True)
    except Exception as exc:  # noqa: BLE001
        query_err = str(exc)
        query_tenant_no_traverse = None
        query_tenant_traverse = None
    query_elapsed = time.perf_counter() - t0

    leaf_ok = query_err is None and all(
        entry.get("query_count") == entry["facade_count"] for entry in per_project
    )
    tenant_trap = (
        query_tenant_no_traverse is not None
        and query_tenant_traverse is not None
        and query_tenant_no_traverse < query_tenant_traverse
    )
    traverse_parity = (
        query_err is None
        and query_tenant_traverse is not None
        and query_tenant_traverse == facade_traverse_total
    )

    return [
        ProbeResult(
            name="tenant-finding-totals-sample-sum",
            elapsed_s=sample_elapsed,
            ok=True,
            detail={
                "workflow": "estate finding denominators",
                "sample_projects": len(projects),
                "per_project_sum": per_project_sum,
                "per_project": per_project,
            },
        ),
        ProbeResult(
            name="tenant-finding-totals-facade-traverse",
            elapsed_s=traverse_elapsed,
            ok=True,
            detail={
                "method": "Finding.count(traverse=True) at tenant root",
                "total": facade_traverse_total,
                "note": "Full tenant traverse count (no max_pages cap)",
            },
        ),
        ProbeResult(
            name="tenant-finding-totals-query",
            elapsed_s=query_elapsed,
            ok=leaf_ok and tenant_trap and traverse_parity and query_err is None,
            detail={
                "workflow": "Query.at_namespace-style root Finding count",
                "per_project": per_project,
                "query_tenant_root_no_traverse": query_tenant_no_traverse,
                "query_tenant_root_traverse": query_tenant_traverse,
                "facade_traverse_total": facade_traverse_total,
                "traverse_parity": traverse_parity,
                "per_project_sum": per_project_sum,
                "leaf_ok": leaf_ok,
                "tenant_root_trap_observed": tenant_trap,
                "error": query_err,
            },
        ),
    ]


def probe_query_escape_hatch_group_by_time(
    client: Any, namespace: str, *, findinglog_days: int = 7
) -> list[ProbeResult]:
    """QuerySpec.list_parameters escape hatch still sends group_by_time on the wire."""
    tenant = resolve_tenant(namespace)
    end = datetime.now(UTC).replace(microsecond=0)
    start = end - timedelta(days=findinglog_days)
    base = reachable_vuln_log_base_filter()
    time_filt = finding_log_time_window_filter(start, end, base_filter=base)
    filt = to_query_filter(
        f"{time_filt} and spec.operation==OPERATION_CREATE "
        "and spec.level in [FINDING_LEVEL_CRITICAL, FINDING_LEVEL_HIGH]"
    )

    t0 = time.perf_counter()
    try:
        spec = (
            QuerySpec.root("FindingLog")
            .filter(filt)
            .list_parameters(
                traverse=True,
                group_by_time=_group_by_time_wire(start=start, end=end),
            )
            .to_wire()
        )
        result = query_create(
            client,
            namespace=tenant,
            name="probe-escape-hatch-gbt",
            query_spec=spec,
        )
        grp = extract_group_response(result)
        list_objects = extract_query_objects(result)
        if grp:
            err = "unexpected group_response"
            ok = False
        elif list_objects:
            err = (
                "QuerySpec.list_parameters(group_by_time=...) still routes to list.objects — "
                "use facade list_groups"
            )
            ok = False
        else:
            err = "empty query_response"
            ok = False
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
        ok = False
        list_objects = []
        grp = {}
    elapsed = time.perf_counter() - t0

    return [
        ProbeResult(
            name="query-escape-hatch-group-by-time",
            elapsed_s=elapsed,
            ok=ok,
            detail={
                "workflow": "removed QuerySpec.group_by_time() — kwargs escape hatch",
                "sdk_path": "QuerySpec.root(...).list_parameters(group_by_time=...)",
                "error": err,
                "query_list_objects": len(list_objects) if list_objects else 0,
                "has_group_response": bool(grp),
                "expected_unsupported": True,
            },
        )
    ]


def probe_authlog_group_by_time(
    client: Any, namespace: str, *, findinglog_days: int = 7
) -> list[ProbeResult]:
    """Workflow: auth login trends — facade list_groups vs Query group_by_time."""
    from endorlabs.workflows.auth.authentication_log import auth_log_filter
    from endorlabs.workflows.logs.group_by_time import group_by_time_counts

    tenant = resolve_tenant(namespace)
    end = datetime.now(UTC).replace(microsecond=0)
    start = end - timedelta(days=findinglog_days)
    filt = auth_log_filter(findinglog_days)
    window_label = f"{start.isoformat()} .. {end.isoformat()} ({findinglog_days}d)"

    t0 = time.perf_counter()
    try:
        facade_buckets = group_by_time_counts(
            client.AuthenticationLog.list_groups,
            namespace=tenant,
            filter=filt,
            traverse=True,
            interval="day",
        )
        facade_ok = True
        facade_err = None
    except Exception as exc:  # noqa: BLE001
        facade_buckets = {}
        facade_ok = False
        facade_err = str(exc)
    facade_elapsed = time.perf_counter() - t0

    query_result = _query_group_by_time_negative(
        client,
        kind="AuthenticationLog",
        namespace=tenant,
        filt=filt,
        traverse=True,
        start=start,
        end=end,
        probe_name="authlog-group-by-time-query",
        workflow="endor-auth-login-count (group_by_time)",
    )

    return [
        ProbeResult(
            name="authlog-group-by-time-facade",
            elapsed_s=facade_elapsed,
            ok=facade_ok,
            detail={
                "window": window_label,
                "bucket_count": len(facade_buckets),
                "sample_buckets": dict(list(facade_buckets.items())[:3]),
                "error": facade_err,
            },
        ),
        query_result,
    ]


def probe_nested_finding_mask(client: Any, namespace: str, *, cap: int) -> list[ProbeResult]:
    """Workflow: estate collect mask — sub-field masks on Query list refs."""
    project, _ = _find_project_with_findings(client, namespace, scan_cap=max(cap, 25))
    if project is None:
        return [
            ProbeResult(
                name="nested-finding-mask",
                elapsed_s=0.0,
                ok=True,
                detail={"note": "No estate findings in sample — skipped", "skipped": True},
            )
        ]

    uid = str(project["uuid"])
    leaf_ns = project_wire_namespace(project)
    filt = to_query_filter(estate_findings_filter())
    scoped = f"{filt} and spec.project_uuid=={uid!r}"
    mask = DEFAULT_ESTATE_FINDING_MASK

    t0 = time.perf_counter()
    facade_rows = client.Finding.list(
        namespace=leaf_ns,
        filter=scoped,
        mask=mask,
        traverse=False,
        max_pages=2,
    )
    facade_elapsed = time.perf_counter() - t0

    t0 = time.perf_counter()
    query_rows = client.Query.Project.collect_estate_findings(
        [project],
        mask=mask,
        max_root_pages=2,
    )
    query_elapsed = time.perf_counter() - t0

    facade_by_uuid = {_row_uuid(row): wire_dict(row) for row in facade_rows if _row_uuid(row)}
    query_by_uuid = {_row_uuid(row): wire_dict(row) for row in query_rows if _row_uuid(row)}
    shared = set(facade_by_uuid) & set(query_by_uuid)

    empty_in_query: list[dict[str, Any]] = []
    for field_path in MASK_PROBE_FIELDS:
        for finding_uuid in list(shared)[:20]:
            facade_val = _nested_field(facade_by_uuid[finding_uuid], field_path)
            query_val = _nested_field(query_by_uuid[finding_uuid], field_path)
            if facade_val and not query_val:
                empty_in_query.append(
                    {"uuid": finding_uuid, "field": field_path, "facade": facade_val}
                )

    ok = len(empty_in_query) == 0

    return [
        ProbeResult(
            name="nested-finding-mask-facade",
            elapsed_s=facade_elapsed,
            ok=True,
            detail={
                "workflow": "estate findings collect mask",
                "mask": mask,
                "rows": len(facade_rows),
            },
        ),
        ProbeResult(
            name="nested-finding-mask-query",
            elapsed_s=query_elapsed,
            ok=ok,
            detail={
                "workflow": "Query nested Finding list ref mask parity",
                "shared_uuids": len(shared),
                "empty_subfields_in_query": empty_in_query[:10],
                "empty_count": len(empty_in_query),
                "note": (
                    "If empty_count>0, mask parent structs (see scan-latest-join) "
                    "instead of deep sub-field paths"
                ),
            },
        ),
    ]


PROBES = {
    "recipe-parity": probe_recipe_parity,
    "prf-counts": probe_prf_counts,
    "finding-list-join": probe_finding_list_join,
    "findinglog-group": probe_findinglog_group,
    "dm-group": probe_dm_group,
    "nested-list": probe_nested_list,
    "scan-latest-join": probe_scan_latest_join,
    "collect-row-parity": probe_collect_row_parity,
    "probe-ref-pagination-wire": probe_ref_pagination_wire,
    "collect-prf-rows": probe_collect_prf_rows,
    "malware-category-split": probe_malware_category_split,
    "severity-validate-sample": probe_severity_validate_sample,
    "tenant-finding-totals": probe_tenant_finding_totals,
    "query-escape-hatch-group-by-time": probe_query_escape_hatch_group_by_time,
    "authlog-group-by-time": probe_authlog_group_by_time,
    "nested-finding-mask": probe_nested_finding_mask,
}

_TIME_WINDOW_PROBES = frozenset(
    {
        "findinglog-group",
        "query-escape-hatch-group-by-time",
        "authlog-group-by-time",
    }
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query workflow replacement probes")
    parser.add_argument(
        "probe",
        choices=[*PROBES.keys(), "all"],
        help="Which workflow pattern to probe",
    )
    parser.add_argument("-n", "--namespace", required=True, help="Tenant or child namespace")
    parser.add_argument("--max-projects", type=int, default=5, help="Sample cap for project-scoped probes")
    parser.add_argument(
        "--findinglog-days",
        type=int,
        default=7,
        help="FindingLog probe window (default: last 7 days)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(".tmp/query_workflow_probes/results"),
        help="Directory for JSON reports",
    )
    args = parser.parse_args(argv)

    names = list(PROBES.keys()) if args.probe == "all" else [args.probe]
    all_results: dict[str, list[dict[str, Any]]] = {}
    exit_code = 0

    with make_client(args.namespace) as client:
        for name in names:
            _log(f"\n=== {name} ===")
            fn = PROBES[name]
            if name in _TIME_WINDOW_PROBES:
                results = fn(
                    client, args.namespace, findinglog_days=args.findinglog_days
                )
            elif name == "dm-group":
                results = fn(client, args.namespace, cap=args.max_projects)
            else:
                results = fn(client, args.namespace, cap=args.max_projects)
            serialized = [r.to_dict() for r in results]
            all_results[name] = serialized
            for r in results:
                status = "OK" if r.ok else "FAIL"
                _log(f"  [{status}] {r.name} ({r.elapsed_s:.2f}s) {r.detail}")
                if not r.ok:
                    if r.detail.get("expected_unsupported"):
                        _log("       (expected unsupported — documented Query gap)")
                    else:
                        exit_code = 1

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_path = args.out / f"{args.namespace.replace('.', '_')}_{stamp}.json"
    write_report(
        out_path,
        {
            "namespace": args.namespace,
            "probe": args.probe,
            "results": all_results,
        },
    )
    _log(f"\nWrote {out_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
