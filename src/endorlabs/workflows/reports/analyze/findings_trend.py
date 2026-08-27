"""SCA (vulnerability) burndown + scan throughput for the report packet.

FindingLog severity×reach series primitives live in
``endorlabs.workflows.findings.finding_log_trends``; this module orchestrates
path/tag rollups and ScanResult throughput for ``report_packet.v0``.

Tag series use **project-grain** pulls (one matrix per tagged project) then
local redistribute. Path series still use leaf-namespace aggregates so untagged
projects are included.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from endorlabs.workflows.findings.finding_log_trends import (
    CHART_DEFAULT_LOOKBACK,
    FINDING_CRITERIA,
)
from endorlabs.workflows.reports.analyze.burndown_common import (
    DEFAULT_BURNDOWN_WORKERS,
    SEV_KEYS,
    build_category_burndown_block,
    sum_severity_facet_matrices,
)
from endorlabs.workflows.reports.analyze.finding_burndown_specs import (
    CATEGORY_SCA,
    SCA_FACET_KEYS,
)

if TYPE_CHECKING:
    from endorlabs import Client

MAIN_LOOKBACK_DAYS = 91
CI_LOOKBACK_DAYS = 21

_SEV_KEYS = SEV_KEYS
_REACH_KEYS = SCA_FACET_KEYS


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_create_time(row: Any) -> datetime | None:
    raw: Any
    if isinstance(row, dict):
        raw = (row.get("meta") or {}).get("create_time")
    else:
        meta = getattr(row, "meta", None)
        raw = getattr(meta, "create_time", None)
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    text = str(raw).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def probe_scan_history_bounds(
    client: Client,
    leaf_namespaces: list[str],
    *,
    max_workers: int = 8,
) -> dict[str, Any]:
    """Return newest/oldest ScanResult create times across *leaf_namespaces*.

    Used as an observed retention / activity bound for throughput captions.
    One newest + one oldest list per leaf (``max_pages=1``); no full scan pull.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    newest: datetime | None = None
    oldest: datetime | None = None
    leaves = [ns for ns in leaf_namespaces if ns]

    def _leaf_bounds(ns: str) -> tuple[datetime | None, datetime | None]:
        try:
            newest_rows = client.ScanResult.list(
                namespace=ns,
                traverse=False,
                sort_by="meta.create_time",
                desc=True,
                mask="uuid,meta.create_time",
                max_pages=1,
                page_size=1,
            )
            oldest_rows = client.ScanResult.list(
                namespace=ns,
                traverse=False,
                sort_by="meta.create_time",
                desc=False,
                mask="uuid,meta.create_time",
                max_pages=1,
                page_size=1,
            )
        except Exception:
            return None, None
        leaf_newest = _row_create_time(newest_rows[0]) if newest_rows else None
        leaf_oldest = _row_create_time(oldest_rows[0]) if oldest_rows else None
        return leaf_newest, leaf_oldest

    if leaves:
        workers = max(1, min(max_workers, len(leaves)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(_leaf_bounds, ns) for ns in leaves]
            for fut in as_completed(futs):
                leaf_newest, leaf_oldest = fut.result()
                if leaf_newest is not None and (newest is None or leaf_newest > newest):
                    newest = leaf_newest
                if leaf_oldest is not None and (oldest is None or leaf_oldest < oldest):
                    oldest = leaf_oldest
    span_days: float | None = None
    if newest is not None and oldest is not None:
        span_days = round((newest - oldest).total_seconds() / 86400.0, 1)
    return {
        "lastScanAt": newest.isoformat() if newest else None,
        "oldestScanAt": oldest.isoformat() if oldest else None,
        "observedRetentionDays": span_days,
    }


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

    leaves = [ns for ns in leaf_namespaces if ns]
    main_f = (
        f"meta.create_time>=date({_iso(main_start)}) and "
        "context.type==CONTEXT_TYPE_MAIN"
    )
    ci_f = (
        f"meta.create_time>=date({_iso(ci_start)}) and "
        "context.type==CONTEXT_TYPE_CI_RUN"
    )

    def _leaf_maps(ns: str) -> tuple[dict[str, int], dict[str, int]]:
        import contextlib

        main_local: dict[str, int] = {}
        ci_local: dict[str, int] = {}
        with contextlib.suppress(Exception):
            main_local = _group_parent_counts(ns, main_f)
        with contextlib.suppress(Exception):
            ci_local = _group_parent_counts(ns, ci_f)
        return main_local, ci_local

    if leaves:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        workers = max(1, min(8, len(leaves)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(_leaf_maps, ns) for ns in leaves]
            for fut in as_completed(futs):
                main_local, ci_local = fut.result()
                for uid, n in main_local.items():
                    main_map[uid] += n
                for uid, n in ci_local.items():
                    ci_map[uid] += n

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
        public = {
            k: v
            for k, v in p.items()
            if k
            in {
                "uuid",
                "name",
                "namespace",
                "tags",
                "create_time",
            }
        }
        enriched.append(
            {
                **public,
                "mainScans91d": main,
                "ciRunScans21d": int(scans.get("ciRunScans21d", 0)),
                "mainScansPerWeek": round(main / (MAIN_LOOKBACK_DAYS / 7), 2),
            }
        )
    project_count = len(enriched)
    main_total = sum(int(p["mainScans91d"]) for p in enriched)
    return {
        "projectCount": project_count,
        "mainScans91d": main_total,
        "ciRunScans21d": sum(int(p["ciRunScans21d"]) for p in enriched),
        "avgMainScansPerProject": round(main_total / max(1, project_count), 2),
        "avgMainPerWeek": round(
            sum(float(p["mainScansPerWeek"]) for p in enriched) / max(1, project_count),
            2,
        ),
        "topProjects": sorted(
            enriched,
            key=lambda r: (
                -int(r["mainScans91d"]),
                -int(r["ciRunScans21d"]),
                str(r.get("uuid") or ""),
            ),
        )[:15],
    }


def sum_severity_reach_matrices(
    parts: list[dict[str, dict[str, dict[str, Any]]]],
    *,
    categories: list[str],
    period_caption: str,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Sum severity×reach series matrices cell-wise."""
    return sum_severity_facet_matrices(
        parts,
        categories=categories,
        period_caption=period_caption,
        facet_keys=_REACH_KEYS,
    )


def build_sca_burndown_report(
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
    """Build SCA (vulnerability) FindingLog series filters, tag series, and throughput.

    Uses the same category-spec + path/tag redistribute path as code findings,
    with ``expand="reach"`` so ``all`` remains RF+PRF.
    """
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=2) as pool:
        burndown_fut = pool.submit(
            build_category_burndown_block,
            client,
            tenant=tenant,
            projects=projects,
            leaf_namespaces=leaf_namespaces,
            path_options=path_options,
            tag_catalog=tag_catalog,
            category_key=CATEGORY_SCA,
            lookback=lookback,
            min_projects=min_projects,
            max_workers=max_workers,
        )
        throughput_fut = pool.submit(
            collect_scan_throughput, client, projects, leaf_namespaces
        )
        bounds_fut = pool.submit(probe_scan_history_bounds, client, leaf_namespaces)
        block = burndown_fut.result()
        scan_by_uuid = throughput_fut.result()
        scan_bounds = bounds_fut.result()
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
        "findingCriteria": block.get("findingCriteria") or FINDING_CRITERIA,
        "lookback": lookback,
        "interval": "week",
        "facetKeys": block.get("facetKeys") or list(SCA_FACET_KEYS),
        "expand": block.get("expand") or "reach",
        "seriesFilters": block["seriesFilters"],
        "tagSeries": block["tagSeries"],
        "tagSeriesMeta": block["tagSeriesMeta"],
        "throughput": {
            "windows": {
                "mainDays": MAIN_LOOKBACK_DAYS,
                "ciRunDays": CI_LOOKBACK_DAYS,
                **scan_bounds,
            },
            "perPath": tp_per_path,
            "perTag": tp_per_tag,
        },
        "periodCaption": block.get("periodCaption"),
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
    min_projects: int = 1,
    max_workers: int = DEFAULT_BURNDOWN_WORKERS,
) -> dict[str, Any]:
    """Compat alias for :func:`build_sca_burndown_report`."""
    return build_sca_burndown_report(
        client,
        tenant=tenant,
        projects=projects,
        leaf_namespaces=leaf_namespaces,
        path_options=path_options,
        tag_catalog=tag_catalog,
        lookback=lookback,
        min_projects=min_projects,
        max_workers=max_workers,
    )
