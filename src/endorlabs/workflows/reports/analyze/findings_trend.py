"""Findings burndown + scan throughput for the report packet.

FindingLog severity×reach series primitives live in
``endorlabs.workflows.findings.finding_log_trends``; this module orchestrates
path/tag rollups and ScanResult throughput for ``report_packet.v0``.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from endorlabs.workflows.findings.finding_log_trends import (
    CHART_DEFAULT_LOOKBACK,
    FINDING_CRITERIA,
    REACHABLE_FUNCTION_CLAUSE,
    compute_window,
    query_severity_reach_matrix,
    query_severity_reach_series_cell,
    sum_series_cells,
)

if TYPE_CHECKING:
    from endorlabs import Client

MAIN_LOOKBACK_DAYS = 91
CI_LOOKBACK_DAYS = 21


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


def build_findings_burndown_report(
    client: Client,
    *,
    tenant: str,
    projects: list[dict[str, Any]],
    leaf_namespaces: list[str],
    path_options: list[str],
    tag_catalog: list[dict[str, Any]],
    lookback: int = CHART_DEFAULT_LOOKBACK,
    min_projects: int = 5,
) -> dict[str, Any]:
    """Build FindingLog series filters, tag series, and throughput."""
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

    def roll_path(path: str) -> dict[str, dict[str, dict[str, Any]]]:
        if path == "all":
            keys = list(leaf_cells)
        else:
            keys = [ns for ns in leaf_cells if ns == path or ns.startswith(path + ".")]
        built: dict[str, dict[str, dict[str, Any]]] = {}
        for sev in ("all", "critical", "high"):
            built[sev] = {}
            for reach in ("all", "reachable", "prf"):
                parts = [
                    leaf_cells[ns][sev][reach]
                    for ns in keys
                    if sev in leaf_cells[ns] and reach in leaf_cells[ns][sev]
                ]
                built[sev][reach] = sum_series_cells(
                    parts, categories=categories, period_caption=period_caption
                )
        return built

    series_filters = {"perPath": {path: roll_path(path) for path in path_options}}

    by_uuid = {p["uuid"]: p for p in projects}
    per_tag: dict[str, dict[str, dict[str, dict[str, dict[str, Any]]]]] = {}
    ready: list[str] = []
    pending: list[str] = []
    for entry in tag_catalog:
        tag = entry["tag"]
        uuids = [u for u in entry.get("projectUuids") or [] if u in by_uuid]
        if len(uuids) < min_projects:
            pending.append(tag)
            continue
        tagged = [by_uuid[u] for u in uuids]
        tag_leaf: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
        for ns in leaf_namespaces:
            ns_uuids = [p["uuid"] for p in tagged if p.get("namespace") == ns]
            if not ns_uuids:
                continue
            tag_leaf[ns] = query_severity_reach_matrix(
                client,
                namespace=ns,
                window_start=window_start,
                window_end=window_end,
                parent_uuids=ns_uuids,
                lookback=lookback,
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
            built: dict[str, dict[str, dict[str, Any]]] = {}
            for sev in ("all", "critical", "high"):
                built[sev] = {}
                for reach in ("all", "reachable", "prf"):
                    parts = [
                        tag_leaf[ns][sev][reach]
                        for ns in keys
                        if sev in tag_leaf[ns] and reach in tag_leaf[ns][sev]
                    ]
                    built[sev][reach] = sum_series_cells(
                        parts, categories=categories, period_caption=period_caption
                    )
            path_map[path] = built
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
            "pullPolicy": {"minProjects": min_projects, "mode": "tag_scoped"},
        },
        "throughput": {
            "windows": {"mainDays": MAIN_LOOKBACK_DAYS, "ciRunDays": CI_LOOKBACK_DAYS},
            "perPath": tp_per_path,
            "perTag": tp_per_tag,
        },
        "periodCaption": period_caption,
    }
