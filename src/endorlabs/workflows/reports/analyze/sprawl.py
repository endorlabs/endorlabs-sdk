"""Version sprawl cube from DependencyMetadata list_groups."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from endorlabs.core.types import ListParameters
from endorlabs.workflows.reports.schemas.packet_v0 import (
    HIST_KEYS,
    empty_sprawl_cell,
    hist_bucket,
)

if TYPE_CHECKING:
    from endorlabs import Client

_PACKAGE_NAME_PATH = "spec.dependency_data.package_name"
_PACKAGE_VERSION_PATH = "spec.dependency_data.resolved_version"
_DIRECT_PATH = "spec.dependency_data.direct"
_PUBLIC_PATH = "spec.dependency_data.public"

_RELATION_KEYS = ("all", "direct", "transitive")
_VISIBILITY_KEYS = ("all", "public", "private")

# Leaf record: package name, resolved version, is_direct, is_public (None = unknown).
LeafPair = tuple[str, str, bool | None, bool | None]

_ECOSYSTEM_PREFIX = {
    "npm://": "npm",
    "pypi://": "PyPI",
    "mvn://": "Maven",
    "go://": "Go",
    "cargo://": "Cargo",
    "gem://": "RubyGems",
    "nuget://": "NuGet",
}


def _ecosystem(package_name: str) -> str:
    for prefix, label in _ECOSYSTEM_PREFIX.items():
        if package_name.startswith(prefix):
            return label
    if "://" in package_name:
        return package_name.split("://", 1)[0]
    return "other"


def _as_bool(value: Any) -> bool | None:
    if value is True or str(value).lower() == "true":
        return True
    if value is False or str(value).lower() == "false":
        return False
    return None


def _normalize_leaf_record(item: Any) -> LeafPair | None:
    """Accept ``(name, ver)`` or ``(name, ver, direct, public)`` tuples."""
    if not isinstance(item, (list, tuple)) or len(item) < 2:
        return None
    name = str(item[0] or "")
    ver = str(item[1] or "")
    if not name or not ver:
        return None
    if len(item) >= 4:
        return name, ver, _as_bool(item[2]), _as_bool(item[3])
    return name, ver, None, None


def _summarize(
    versions_by_pkg: dict[str, set[str]],
    *,
    top_n: int = 10,
) -> dict[str, Any]:
    if not versions_by_pkg:
        return empty_sprawl_cell()
    counts = {name: len(vs) for name, vs in versions_by_pkg.items()}
    hist = {k: 0 for k in HIST_KEYS}
    hist_v = {k: 0 for k in HIST_KEYS}
    for n in counts.values():
        key = hist_bucket(n)
        hist[key] += 1
        hist_v[key] += n
    total_p = len(counts)
    total_v = sum(counts.values())
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
    return {
        "p": total_p,
        "v": total_v,
        "max": max(counts.values()) if counts else 0,
        "avg": round(total_v / total_p, 2) if total_p else 0.0,
        "h": [hist[k] for k in HIST_KEYS],
        "hv": [hist_v[k] for k in HIST_KEYS],
        "t": [[name, n] for name, n in top],
    }


def _grouped_count_list_parameters(*, page_size: int) -> ListParameters:
    return ListParameters(
        traverse=False,
        page_size=page_size,
        group_aggregation_paths=[
            _PACKAGE_NAME_PATH,
            _PACKAGE_VERSION_PATH,
            _DIRECT_PATH,
            _PUBLIC_PATH,
        ],
    )


def _record_from_bucket(bucket: Any) -> LeafPair | None:
    parsed = getattr(bucket, "parsed", None) or {}
    name = str(parsed.get(_PACKAGE_NAME_PATH) or "")
    ver = str(parsed.get(_PACKAGE_VERSION_PATH) or "")
    if not name or not ver:
        return None
    return (
        name,
        ver,
        _as_bool(parsed.get(_DIRECT_PATH)),
        _as_bool(parsed.get(_PUBLIC_PATH)),
    )


def collect_leaf_pairs(
    client: Client,
    leaf_namespaces: list[str],
    *,
    page_size: int = 500,
) -> dict[str, list[LeafPair]]:
    """Return ``{namespace: [(name, version, direct, public), ...]}`` distinct rows."""
    out: dict[str, list[LeafPair]] = {}
    lp = _grouped_count_list_parameters(page_size=page_size)
    paths = [
        _PACKAGE_NAME_PATH,
        _PACKAGE_VERSION_PATH,
        _DIRECT_PATH,
        _PUBLIC_PATH,
    ]
    for ns in leaf_namespaces:
        buckets = list(
            client.DependencyMetadata.list_groups(
                namespace=ns,
                list_params=lp,
                paths=paths,
                max_pages=None,
            )
        )
        seen: set[LeafPair] = set()
        pairs: list[LeafPair] = []
        for b in buckets:
            rec = _record_from_bucket(b)
            if rec is None or rec in seen:
                continue
            seen.add(rec)
            pairs.append(rec)
        out[ns] = pairs
    return out


def _passes_relation(direct: bool | None, relation: str) -> bool:
    if relation == "all":
        return True
    if relation == "direct":
        return direct is True
    if relation == "transitive":
        return direct is False
    return False


def _passes_visibility(public: bool | None, visibility: str) -> bool:
    if visibility == "all":
        return True
    if visibility == "public":
        return public is True
    if visibility == "private":
        return public is False
    return False


def build_version_sprawl_report(
    *,
    leaf_pairs: dict[str, list[Any]],
    path_options: list[str],
    projects: list[dict[str, Any]],
    tag_catalog: list[dict[str, Any]],
) -> dict[str, Any]:
    """Roll leaf package×version rows into estate / path / tag grids.

    Grid shape: ``[ecosystem][relation][visibility]`` where relation is
    ``all|direct|transitive`` and visibility is ``all|public|private``.
    """
    normalized: dict[str, list[LeafPair]] = {}
    for ns, rows in leaf_pairs.items():
        kept: list[LeafPair] = []
        for item in rows:
            rec = _normalize_leaf_record(item)
            if rec is not None:
                kept.append(rec)
        normalized[ns] = kept

    uuid_ns = {p["uuid"]: p.get("namespace") or "" for p in projects}
    tag_namespaces: dict[str, set[str]] = {}
    for entry in tag_catalog:
        tag = entry["tag"]
        nss: set[str] = set()
        for uid in entry.get("projectUuids") or []:
            ns = uuid_ns.get(uid)
            if ns:
                nss.add(ns)
        tag_namespaces[tag] = nss

    def versions_for_namespaces(
        nss: set[str],
        *,
        relation: str = "all",
        visibility: str = "all",
        ecosystem: str = "all",
    ) -> dict[str, set[str]]:
        by: dict[str, set[str]] = defaultdict(set)
        for ns in nss:
            for name, ver, direct, public in normalized.get(ns, []):
                if not _passes_relation(direct, relation):
                    continue
                if not _passes_visibility(public, visibility):
                    continue
                if ecosystem != "all" and _ecosystem(name) != ecosystem:
                    continue
                by[name].add(ver)
        return by

    all_leaves = set(normalized)
    ecosystems = sorted(
        {
            _ecosystem(name)
            for pairs in normalized.values()
            for name, _ver, _d, _p in pairs
        }
    )

    def grid_for(nss: set[str]) -> dict[str, dict[str, dict[str, dict[str, Any]]]]:
        grid: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
        eco_keys = ["all", *ecosystems]
        for eco in eco_keys:
            grid[eco] = {}
            for relation in _RELATION_KEYS:
                grid[eco][relation] = {}
                for visibility in _VISIBILITY_KEYS:
                    grid[eco][relation][visibility] = _summarize(
                        versions_for_namespaces(
                            nss,
                            relation=relation,
                            visibility=visibility,
                            ecosystem=eco,
                        )
                    )
        return grid

    per_path: dict[str, dict[str, dict[str, dict[str, dict[str, Any]]]]] = {}
    for path in path_options:
        if path == "all":
            nss = all_leaves
        else:
            nss = {ns for ns in all_leaves if ns == path or ns.startswith(path + ".")}
        per_path[path] = grid_for(nss)

    per_tag: dict[str, dict[str, dict[str, dict[str, dict[str, Any]]]]] = {}
    for tag, nss in tag_namespaces.items():
        scoped = nss & all_leaves
        if not scoped:
            continue
        per_tag[tag] = grid_for(scoped)

    return {
        "histKeys": list(HIST_KEYS),
        "ecosystems": ecosystems,
        "relations": list(_RELATION_KEYS),
        "visibilities": list(_VISIBILITY_KEYS),
        "estate": per_path.get("all", grid_for(all_leaves)),
        "perPath": per_path,
        "perTag": per_tag,
    }
