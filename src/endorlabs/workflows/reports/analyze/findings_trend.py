"""Findings burndown + scan throughput for the report packet.

FindingLog severity×reach series primitives live in
``endorlabs.workflows.findings.finding_log_trends``; this module orchestrates
path/tag rollups and ScanResult throughput for ``report_packet.v0``.

Tag series use **project-grain** pulls (one matrix per tagged project) then
local redistribute. Path series still use leaf-namespace aggregates so untagged
projects are included.
"""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from endorlabs.workflows.findings.finding_log_trends import (
    CHART_DEFAULT_LOOKBACK,
    FINDING_CRITERIA,
    REACHABLE_FUNCTION_CLAUSE,
    compute_window,
    empty_series_cell,
    query_severity_reach_matrix,
    query_severity_reach_series_cell,
    sum_series_cells,
)

if TYPE_CHECKING:
    from endorlabs import Client

MAIN_LOOKBACK_DAYS = 91
CI_LOOKBACK_DAYS = 21
DEFAULT_BURNDOWN_WORKERS = 24
PULL_MODE_PROJECT_GRAIN = "project_grain_redistribute"

_SEV_KEYS = ("all", "critical", "high")
_REACH_KEYS = ("all", "reachable", "prf")


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def collect_scan_throughput(
    client: Client,
    projects: list[dict[str, Any]],
    leaf_namespaces: list[str],
) -> dict[str, dict[str, int]]:
    """Return ``{project_uuid: {mainScans91d, ciRunScans21d}}``."""
    from endorlabs.core.types import ListParameters
    from endorlabs.operations.list_response import group_bucket_count

    now = datetime.now(UTC)
    main_start = now - timedelta(days=MAIN_LOOKBACK_DAYS)
    ci_start = now - timedelta(days=CI_LOOKBACK_DAYS)
    main_map: dict[str, int] = defaultdict(int)
    ci_map: dict[str, int] = defaultdict(int)

    def _group_parent_counts(namespace: str, filt: str) -> dict[str, int]:
        lp = ListParameters(
            traverse=False,
            group=True,
            group_aggregation_paths=["meta.parent_uuid"],
            filter=filt,
        )
        counts: dict[str, int] = defaultdict(int)
        buckets = list(
            client.ScanResult.list_groups(
                namespace=namespace,
                traverse=False,
                filter=filt,
                list_params=lp,
                paths=["meta.parent_uuid"],
                max_pages=None,
            )
        )
        for b in buckets:
            parsed = getattr(b, "parsed", None) or {}
            parent = str(parsed.get("meta.parent_uuid") or "")
            if parent:
                counts[parent] += int(group_bucket_count(b) or 0)
        return counts

    for ns in leaf_namespaces:
        main_f = (
            f"meta.create_time>=date({_iso(main_start)}) and "
            "context.type==CONTEXT_TYPE_MAIN"
        )
        ci_f = (
            f"meta.create_time>=date({_iso(ci_start)}) and "
            "context.type==CONTEXT_TYPE_CI_RUN"
        )
        try:
            for uid, n in _group_parent_counts(ns, main_f).items():
                main_map[uid] += n
        except Exception:
            pass
        try:
            for uid, n in _group_parent_counts(ns, ci_f).items():
                ci_map[uid] += n
        except Exception:
            pass

    out: dict[str, dict[str, int]] = {}
    for p in projects:
        uid = p["uuid"]
        out[uid] = {
            "mainScans91d": int(main_map.get(uid, 0)),
            "ciRunScans21d": int(ci_map.get(uid, 0)),
        }
    return out


def _throughput_scope(
    projects: list[dict[str, Any]],
    scan_by_uuid: dict[str, dict[str, int]],
) -> dict[str, Any]:
    enriched = []
    for p in projects:
        scans = scan_by_uuid.get(p["uuid"], {})
        main = int(scans.get("mainScans91d", 0))
        enriched.append(
            {
                **p,
                "mainScans91d": main,
                "ciRunScans21d": int(scans.get("ciRunScans21d", 0)),
                "mainScansPerWeek": round(main / (MAIN_LOOKBACK_DAYS / 7), 2),
            }
        )
    return {
        "projectCount": len(enriched),
        "mainScans91d": sum(int(p["mainScans91d"]) for p in enriched),
        "ciRunScans21d": sum(int(p["ciRunScans21d"]) for p in enriched),
        "avgMainPerWeek": round(
            sum(float(p["mainScansPerWeek"]) for p in enriched) / max(1, len(enriched)),
            2,
        ),
        "topProjects": sorted(
            enriched, key=lambda r: int(r["mainScans91d"]), reverse=True
        )[:15],
    }


def _empty_matrix(
    categories: list[str], period_caption: str
) -> dict[str, dict[str, dict[str, Any]]]:
    return {
        sev: {
            reach: empty_series_cell(categories, period_caption)
            for reach in _REACH_KEYS
        }
        for sev in _SEV_KEYS
    }


def sum_severity_reach_matrices(
    parts: list[dict[str, dict[str, dict[str, Any]]]],
    *,
    categories: list[str],
    period_caption: str,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Sum severity×reach series matrices cell-wise."""
    if not parts:
        return _empty_matrix(categories, period_caption)
    built: dict[str, dict[str, dict[str, Any]]] = {}
    for sev in _SEV_KEYS:
        built[sev] = {}
        for reach in _REACH_KEYS:
            cells = [
                matrix[sev][reach]
                for matrix in parts
                if sev in matrix and reach in matrix[sev]
            ]
            built[sev][reach] = sum_series_cells(
                cells, categories=categories, period_caption=period_caption
            )
    return built


def _roll_project_matrices(
    project_matrices: dict[str, dict[str, dict[str, dict[str, Any]]]],
    uuids: list[str],
    *,
    categories: list[str],
    period_caption: str,
) -> dict[str, dict[str, dict[str, Any]]]:
    parts = [project_matrices[uid] for uid in uuids if uid in project_matrices]
    return sum_severity_reach_matrices(
        parts, categories=categories, period_caption=period_caption
    )


def _pull_project_matrices(
    client: Client,
    projects: list[dict[str, Any]],
    *,
    window_start: datetime,
    window_end: datetime,
    lookback: int,
    categories: list[str],
    period_caption: str,
    max_workers: int,
) -> dict[str, dict[str, dict[str, dict[str, Any]]]]:
    """Pull one FindingLog severity×reach matrix per project (parallel)."""

    def _one(
        project: dict[str, Any],
    ) -> tuple[str, dict[str, dict[str, dict[str, Any]]]]:
        uid = str(project["uuid"])
        ns = str(project.get("namespace") or "")
        try:
            matrix = query_severity_reach_matrix(
                client,
                namespace=ns,
                window_start=window_start,
                window_end=window_end,
                parent_uuids=[uid],
                lookback=lookback,
                categories=categories,
                period_caption=period_caption,
            )
        except Exception:
            matrix = _empty_matrix(categories, period_caption)
        return uid, matrix

    out: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    if not projects:
        return out
    workers = max(1, max_workers)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one, project) for project in projects]
        for fut in as_completed(futures):
            uid, matrix = fut.result()
            out[uid] = matrix
    return out


def build_findings_burndown_report(
    client: Client,
    *,
    tenant: str,
    projects: list[dict[str, Any]],
    leaf_namespaces: list[str],
    path_options: list[str],
    tag_catalog: list[dict[str, Any]],
    lookback: int = CHART_DEFAULT_LOOKBACK,
    min_projects: int = 1,
    max_workers: int = DEFAULT_BURNDOWN_WORKERS,
) -> dict[str, Any]:
    """Build FindingLog series filters, tag series, and throughput.

    Path series: one matrix per leaf namespace (includes untagged projects).
    Tag series: parallel per-tagged-project matrices, then local redistribute.
    *min_projects* only filters which tags appear in ``tagSeries`` (display);
    it does not skip project pulls.
    """
    window_start, window_end = compute_window(lookback=lookback)
    seed = query_severity_reach_series_cell(
        client,
        namespace=tenant,
        window_start=window_start,
        window_end=window_end,
        reach_clause=REACHABLE_FUNCTION_CLAUSE,
        level="CRITICAL",
        parent_uuids=None,
        lookback=lookback,
    )
    categories = list(seed["categories"])
    period_caption = str(seed["periodCaption"])

    leaf_cells: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for ns in leaf_namespaces:
        try:
            leaf_cells[ns] = query_severity_reach_matrix(
                client,
                namespace=ns,
                window_start=window_start,
                window_end=window_end,
                parent_uuids=None,
                lookback=lookback,
                categories=categories,
                period_caption=period_caption,
            )
        except Exception:
            leaf_cells[ns] = _empty_matrix(categories, period_caption)

    def roll_path(path: str) -> dict[str, dict[str, dict[str, Any]]]:
        if path == "all":
            keys = list(leaf_cells)
        else:
            keys = [ns for ns in leaf_cells if ns == path or ns.startswith(path + ".")]
        return sum_severity_reach_matrices(
            [leaf_cells[ns] for ns in keys],
            categories=categories,
            period_caption=period_caption,
        )

    series_filters = {"perPath": {path: roll_path(path) for path in path_options}}

    by_uuid = {p["uuid"]: p for p in projects}
    tagged_projects = [
        p for p in projects if p.get("tags") and p.get("namespace") and p.get("uuid")
    ]
    project_matrices = _pull_project_matrices(
        client,
        tagged_projects,
        window_start=window_start,
        window_end=window_end,
        lookback=lookback,
        categories=categories,
        period_caption=period_caption,
        max_workers=max_workers,
    )

    per_tag: dict[str, dict[str, dict[str, dict[str, dict[str, Any]]]]] = {}
    ready: list[str] = []
    pending: list[str] = []
    for entry in tag_catalog:
        tag = entry["tag"]
        uuids = [u for u in entry.get("projectUuids") or [] if u in by_uuid]
        if len(uuids) < min_projects:
            pending.append(tag)
            continue
        pulled = [u for u in uuids if u in project_matrices]
        if not pulled:
            pending.append(tag)
            continue
        tagged_rows = [by_uuid[u] for u in pulled]
        tag_leaf: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
        for ns in leaf_namespaces:
            ns_uuids = [p["uuid"] for p in tagged_rows if p.get("namespace") == ns]
            if not ns_uuids:
                continue
            tag_leaf[ns] = _roll_project_matrices(
                project_matrices,
                ns_uuids,
                categories=categories,
                period_caption=period_caption,
            )
        path_map: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
        for path in path_options:
            if path == "all":
                keys = list(tag_leaf)
            else:
                keys = [
                    ns for ns in tag_leaf if ns == path or ns.startswith(path + ".")
                ]
            if not keys:
                continue
            path_map[path] = sum_severity_reach_matrices(
                [tag_leaf[ns] for ns in keys],
                categories=categories,
                period_caption=period_caption,
            )
        if path_map:
            per_tag[tag] = path_map
            ready.append(tag)
        else:
            pending.append(tag)

    scan_by_uuid = collect_scan_throughput(client, projects, leaf_namespaces)
    tp_per_path = {
        path: _throughput_scope(
            [
                p
                for p in projects
                if path == "all"
                or (p.get("namespace") or "") == path
                or (p.get("namespace") or "").startswith(path + ".")
            ],
            scan_by_uuid,
        )
        for path in path_options
    }
    tp_per_tag = {}
    for entry in tag_catalog:
        tag = entry["tag"]
        uuids = set(entry.get("projectUuids") or [])
        rows = [p for p in projects if p["uuid"] in uuids]
        tp_per_tag[tag] = _throughput_scope(rows, scan_by_uuid)

    return {
        "findingCriteria": FINDING_CRITERIA,
        "lookback": lookback,
        "interval": "week",
        "seriesFilters": series_filters,
        "tagSeries": {"tags": ready, "perTag": per_tag},
        "tagSeriesMeta": {
            "seriesReady": ready,
            "seriesPending": pending,
            "seriesReadyCount": len(ready),
            "seriesPendingCount": len(pending),
            "pullPolicy": {
                "minProjects": min_projects,
                "mode": PULL_MODE_PROJECT_GRAIN,
                "taggedProjectsPulled": len(project_matrices),
                "workers": max(1, max_workers),
            },
        },
        "throughput": {
            "windows": {"mainDays": MAIN_LOOKBACK_DAYS, "ciRunDays": CI_LOOKBACK_DAYS},
            "perPath": tp_per_path,
            "perTag": tp_per_tag,
        },
        "periodCaption": period_caption,
    }
