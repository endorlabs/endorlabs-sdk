"""Project discovery, onboarding, and inventory report datasets."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from endorlabs import Client


def _row_namespace(row: Any) -> str:
    if isinstance(row, dict):
        tm = row.get("tenant_meta") or {}
        return str(tm.get("namespace") or "")
    tm = getattr(row, "tenant_meta", None)
    return str(getattr(tm, "namespace", None) or "")


def _row_meta(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row.get("meta") or {})
    meta = getattr(row, "meta", None)
    if meta is None:
        return {}
    if hasattr(meta, "model_dump"):
        return meta.model_dump(mode="json", exclude_none=True)
    return {
        "name": getattr(meta, "name", None),
        "tags": list(getattr(meta, "tags", None) or []),
        "create_time": getattr(meta, "create_time", None),
    }


def _row_uuid(row: Any) -> str:
    if isinstance(row, dict):
        return str(row.get("uuid") or "")
    return str(getattr(row, "uuid", None) or "")


def _row_is_sbom(row: Any) -> bool:
    from endorlabs.resources.project import is_sbom_project_row

    return bool(is_sbom_project_row(row))


def normalize_project_row(row: Any) -> dict[str, Any]:
    """Normalize a Project list/mask row into a plain dict."""
    meta = _row_meta(row)
    tags = [str(t) for t in (meta.get("tags") or []) if t]
    return {
        "uuid": _row_uuid(row),
        "name": str(meta.get("name") or ""),
        "namespace": _row_namespace(row),
        "tags": tags,
        "create_time": str(meta.get("create_time") or ""),
        "is_sbom": _row_is_sbom(row),
    }


def non_sbom_leaf_namespaces(
    projects: list[dict[str, Any]],
    *,
    fallback: str,
) -> list[str]:
    """Leaf namespaces from non-SBOM projects (Java denom / exclude_sbom parity)."""
    leaves = sorted(
        {
            str(p.get("namespace") or "")
            for p in projects
            if p.get("namespace") and not p.get("is_sbom")
        }
    )
    return leaves or [fallback]


def path_options_from_namespaces(namespaces: list[str]) -> list[str]:
    """Inclusive namespace path options rooted at each leaf."""
    paths: set[str] = {"all"}
    for ns in namespaces:
        if not ns:
            continue
        parts = ns.split(".")
        for i in range(1, len(parts) + 1):
            paths.add(".".join(parts[:i]))
    return [
        "all",
        *sorted(
            (p for p in paths if p != "all"),
            key=lambda p: (p.count("."), p),
        ),
    ]


def discover_projects(
    client: Client,
    namespace: str,
    *,
    traverse: bool = True,
) -> dict[str, Any]:
    """List projects and build tag catalog / path options."""
    rows = client.Project.list(
        namespace=namespace,
        traverse=traverse,
        mask=(
            "uuid,meta.name,meta.tags,meta.create_time,tenant_meta.namespace,spec.sbom"
        ),
        max_pages=None,
    )
    projects = [normalize_project_row(r) for r in rows]
    projects = [p for p in projects if p["uuid"]]
    projects.sort(key=lambda p: str(p.get("uuid") or ""))

    by_tag_uuids: dict[str, list[str]] = defaultdict(list)
    tag_counts: Counter[str] = Counter()
    leaf_set: set[str] = set()
    for p in projects:
        if p["namespace"]:
            leaf_set.add(p["namespace"])
        for tag in p["tags"]:
            tag_counts[tag] += 1
            by_tag_uuids[tag].append(p["uuid"])

    catalog = [
        {
            "tag": tag,
            "projectCount": count,
            "projectUuids": sorted(set(by_tag_uuids[tag])),
        }
        for tag, count in sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    leaves = sorted(leaf_set)
    return {
        "projects": projects,
        "tagCatalog": catalog,
        "tagCounts": dict(sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "leafNamespaces": leaves,
        "pathOptions": path_options_from_namespaces(leaves or [namespace]),
    }


def _parse_create(value: str) -> datetime | None:
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _week_monday(dt: datetime) -> datetime:
    dt = dt.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return dt - timedelta(days=dt.weekday())


def build_onboarding_report(projects: list[dict[str, Any]]) -> dict[str, Any]:
    """Build onboarding series from normalized project rows."""
    dated: list[tuple[datetime, dict[str, Any]]] = []
    for p in projects:
        dt = _parse_create(str(p.get("create_time") or ""))
        if dt is None:
            continue
        dated.append((dt, p))
    dated.sort(key=lambda x: x[0])

    by_name: dict[str, tuple[datetime, dict[str, Any]]] = {}
    for dt, p in dated:
        name = str(p.get("name") or "")
        if not name:
            continue
        prev = by_name.get(name)
        if prev is None or dt < prev[0]:
            by_name[name] = (dt, p)

    def weekly_series(
        items: list[tuple[datetime, dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        buckets: dict[str, int] = defaultdict(int)
        for dt, _p in items:
            key = _week_monday(dt).date().isoformat()
            buckets[key] += 1
        weeks = sorted(buckets)
        out: list[dict[str, Any]] = []
        running = 0
        for w in weeks:
            running += buckets[w]
            out.append({"w": w, "n": buckets[w], "c": running})
        return out

    weekly_all = weekly_series(dated)
    weekly_distinct = weekly_series(list(by_name.values()))

    def path_totals(items: list[dict[str, Any]]) -> dict[str, int]:
        totals: dict[str, int] = defaultdict(int)
        for p in items:
            ns = str(p.get("namespace") or "")
            if not ns:
                continue
            parts = ns.split(".")
            for i in range(1, len(parts) + 1):
                totals[".".join(parts[:i])] += 1
        return dict(sorted(totals.items(), key=lambda kv: (-kv[1], kv[0])))

    all_rows = [p for _dt, p in dated]
    distinct_rows = [p for _dt, p in by_name.values()]
    dup_extra = max(0, len(all_rows) - len(distinct_rows))

    return {
        "allRegistrations": len(all_rows),
        "distinctRepositories": len(distinct_rows),
        "duplicateRegistrations": dup_extra,
        "weeklyAll": weekly_all,
        "weeklyDistinct": weekly_distinct,
        "hierarchyAll": [
            {"namespace": k, "count": v} for k, v in path_totals(all_rows).items()
        ],
        "hierarchyDistinct": [
            {"namespace": k, "count": v} for k, v in path_totals(distinct_rows).items()
        ],
        "weekFirst": weekly_all[0]["w"] if weekly_all else "",
        "weekLast": weekly_all[-1]["w"] if weekly_all else "",
    }
