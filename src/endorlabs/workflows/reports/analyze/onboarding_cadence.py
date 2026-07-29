"""ScanResult MAIN/CI cadence for executive onboarding report."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from endorlabs.workflows.logs.group_by_time import group_by_time_counts
from endorlabs.workflows.reports.analyze.findings_trend import MAIN_LOOKBACK_DAYS

if TYPE_CHECKING:
    from endorlabs import Client

CADENCE_LOOKBACK_DAYS = MAIN_LOOKBACK_DAYS
TOP_N = 25

MAIN_FULL_CLAUSE = "context.type==CONTEXT_TYPE_MAIN and spec.type==TYPE_ALL_SCANS"
MAIN_ANY_CLAUSE = "context.type==CONTEXT_TYPE_MAIN"
CI_CLAUSE = "context.type==CONTEXT_TYPE_CI_RUN"


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def cadence_window_filter(
    *,
    lookback_days: int = CADENCE_LOOKBACK_DAYS,
    now: datetime | None = None,
) -> tuple[str, datetime, datetime]:
    """Return ``(time_clause, window_start, window_end)`` for ScanResult cadence."""
    end = now or datetime.now(UTC)
    start = end - timedelta(days=lookback_days)
    return f"meta.create_time>=date({_iso(start)})", start, end


def main_full_filter(window: str) -> str:
    return f"{window} and {MAIN_FULL_CLAUSE}"


def main_with_analytics_filter(window: str) -> str:
    return f"{window} and {MAIN_ANY_CLAUSE}"


def ci_filter(window: str) -> str:
    return f"{window} and {CI_CLAUSE}"


def _weekly_list(buckets: dict[str, int]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key in sorted(buckets):
        day = key[:10] if "T" in key else key
        out.append({"w": day, "n": int(buckets[key])})
    return out


def _group_parent_counts(
    client: Client,
    namespace: str,
    filt: str,
) -> dict[str, int]:
    from endorlabs.core.types import ListParameters
    from endorlabs.operations.list_response import group_bucket_count

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


def _distinct_context_ids(
    client: Client,
    tenant: str,
    filt: str,
) -> int:
    from endorlabs.core.types import ListParameters
    from endorlabs.operations.list_response import group_bucket_count

    lp = ListParameters(
        traverse=True,
        group=True,
        group_aggregation_paths=["context.id"],
        filter=filt,
    )
    try:
        buckets = list(
            client.ScanResult.list_groups(
                namespace=tenant,
                traverse=True,
                filter=filt,
                list_params=lp,
                paths=["context.id"],
                max_pages=None,
            )
        )
    except Exception:
        return 0
    return sum(1 for b in buckets if int(group_bucket_count(b) or 0) > 0)


def _safe_weekly(
    client: Client,
    tenant: str,
    filt: str,
) -> list[dict[str, Any]]:
    try:
        buckets = group_by_time_counts(
            client.ScanResult.list_groups,
            namespace=tenant,
            filter=filt,
            traverse=True,
            interval="week",
        )
        return _weekly_list(buckets)
    except Exception:
        return []


def redistribute_by_tag(
    by_project: dict[str, dict[str, int]],
    tag_catalog: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sum project cadence into tag rows (local; no API)."""
    rows: list[dict[str, Any]] = []
    for entry in tag_catalog:
        tag = str(entry.get("tag") or "")
        if not tag:
            continue
        uuids = [str(u) for u in (entry.get("projectUuids") or []) if u]
        main = 0
        ci = 0
        for uid in uuids:
            cell = by_project.get(uid) or {}
            main += int(cell.get("mainFullScans") or 0)
            ci += int(cell.get("ciScans") or 0)
        pc = int(entry.get("projectCount") or len(uuids) or 0)
        rows.append(
            {
                "tag": tag,
                "projectCount": pc,
                "mainFullScans": main,
                "ciScans": ci,
                "mainPerProject": round(main / max(1, pc), 2),
                "projectUuids": uuids,
            }
        )
    rows.sort(
        key=lambda r: (-int(r["mainFullScans"]), -int(r["ciScans"]), str(r["tag"]))
    )
    return rows


def rank_projects(
    by_project: dict[str, dict[str, int]],
    projects: list[dict[str, Any]],
    *,
    limit: int = TOP_N,
) -> list[dict[str, Any]]:
    """Top projects by MAIN full scans then CI."""
    by_uuid = {str(p["uuid"]): p for p in projects if p.get("uuid")}
    ranked: list[dict[str, Any]] = []
    for uid, cell in by_project.items():
        p = by_uuid.get(uid) or {}
        ranked.append(
            {
                "uuid": uid,
                "name": str(p.get("name") or ""),
                "namespace": str(p.get("namespace") or ""),
                "tags": list(p.get("tags") or []),
                "mainFullScans": int(cell.get("mainFullScans") or 0),
                "ciScans": int(cell.get("ciScans") or 0),
            }
        )
    ranked.sort(
        key=lambda r: (-int(r["mainFullScans"]), -int(r["ciScans"]), str(r["name"]))
    )
    return ranked[: max(0, limit)]


def collect_onboarding_cadence(
    client: Client,
    *,
    tenant: str,
    projects: list[dict[str, Any]],
    leaf_namespaces: list[str],
    tag_catalog: list[dict[str, Any]],
    lookback_days: int = CADENCE_LOOKBACK_DAYS,
    top_n: int = TOP_N,
) -> dict[str, Any]:
    """Build ScanResult cadence block for ``reports.onboarding.cadence``."""
    window, start, end = cadence_window_filter(lookback_days=lookback_days)
    full_f = main_full_filter(window)
    any_f = main_with_analytics_filter(window)
    ci_f = ci_filter(window)

    weekly_main_full = _safe_weekly(client, tenant, full_f)
    weekly_main_analytics = _safe_weekly(client, tenant, any_f)
    weekly_ci = _safe_weekly(client, tenant, ci_f)

    main_map: dict[str, int] = defaultdict(int)
    ci_map: dict[str, int] = defaultdict(int)
    for ns in leaf_namespaces:
        if not ns:
            continue
        try:
            for uid, n in _group_parent_counts(client, ns, full_f).items():
                main_map[uid] += n
        except Exception:
            pass
        try:
            for uid, n in _group_parent_counts(client, ns, ci_f).items():
                ci_map[uid] += n
        except Exception:
            pass

    by_project: dict[str, dict[str, int]] = {}
    for p in projects:
        uid = str(p["uuid"])
        by_project[uid] = {
            "mainFullScans": int(main_map.get(uid, 0)),
            "ciScans": int(ci_map.get(uid, 0)),
        }

    by_tag = redistribute_by_tag(by_project, tag_catalog)
    top_projects = rank_projects(by_project, projects, limit=top_n)
    top_tags = [
        {k: v for k, v in row.items() if k != "projectUuids"} for row in by_tag[:top_n]
    ]

    main_full_total = sum(int(c["mainFullScans"]) for c in by_project.values())
    ci_total = sum(int(c["ciScans"]) for c in by_project.values())
    distinct_prs = _distinct_context_ids(client, tenant, ci_f)

    return {
        "lookbackDays": lookback_days,
        "windowStart": start.isoformat(),
        "windowEnd": end.isoformat(),
        "weeklyMainFull": weekly_main_full,
        "weeklyMainWithAnalytics": weekly_main_analytics,
        "weeklyCi": weekly_ci,
        "byProject": by_project,
        "byTag": [
            {k: v for k, v in row.items() if k != "projectUuids"} for row in by_tag
        ],
        "tagProjectUuids": {row["tag"]: row["projectUuids"] for row in by_tag},
        "topProjects": top_projects,
        "topTags": top_tags,
        "totals": {
            "mainFullScans": main_full_total,
            "ciScans": ci_total,
            "distinctPrContextIds": distinct_prs,
            "projectsWithMainFull": sum(
                1 for c in by_project.values() if int(c["mainFullScans"]) > 0
            ),
        },
    }
