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


def _grouped_count_list_parameters(*, page_size: int) -> ListParameters:
    return ListParameters(
        traverse=False,
        page_size=page_size,
        group_aggregation_paths=[_PACKAGE_NAME_PATH, _PACKAGE_VERSION_PATH],
    )


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


def _pair_from_bucket(bucket: Any) -> tuple[str, str]:
    parsed = getattr(bucket, "parsed", None) or {}
    name = str(parsed.get(_PACKAGE_NAME_PATH) or "")
    ver = str(parsed.get(_PACKAGE_VERSION_PATH) or "")
    return name, ver


def collect_leaf_pairs(
    client: Client,
    leaf_namespaces: list[str],
    *,
    page_size: int = 500,
) -> dict[str, list[tuple[str, str]]]:
    """Return ``{namespace: [(package_name, version), ...]}`` distinct pairs."""
    out: dict[str, list[tuple[str, str]]] = {}
    lp = _grouped_count_list_parameters(page_size=page_size)
    for ns in leaf_namespaces:
        buckets = list(
            client.DependencyMetadata.list_groups(
                namespace=ns,
                list_params=lp,
                paths=[_PACKAGE_NAME_PATH, _PACKAGE_VERSION_PATH],
                max_pages=None,
            )
        )
        seen: set[tuple[str, str]] = set()
        pairs: list[tuple[str, str]] = []
        for b in buckets:
            name, ver = _pair_from_bucket(b)
            if not name or not ver:
                continue
            key = (name, ver)
            if key in seen:
                continue
            seen.add(key)
            pairs.append(key)
        out[ns] = pairs
    return out


def build_version_sprawl_report(
    *,
    leaf_pairs: dict[str, list[tuple[str, str]]],
    path_options: list[str],
    projects: list[dict[str, Any]],
    tag_catalog: list[dict[str, Any]],
) -> dict[str, Any]:
    """Roll leaf package x version pairs into estate / path / tag grids."""
    # UUID → namespace
    uuid_ns = {p["uuid"]: p.get("namespace") or "" for p in projects}
    # tag → namespaces that contain tagged projects
    tag_namespaces: dict[str, set[str]] = {}
    for entry in tag_catalog:
        tag = entry["tag"]
        nss: set[str] = set()
        for uid in entry.get("projectUuids") or []:
            ns = uuid_ns.get(uid)
            if ns:
                nss.add(ns)
        tag_namespaces[tag] = nss

    def versions_for_namespaces(nss: set[str]) -> dict[str, set[str]]:
        by: dict[str, set[str]] = defaultdict(set)
        for ns in nss:
            for name, ver in leaf_pairs.get(ns, []):
                by[name].add(ver)
        return by

    all_leaves = set(leaf_pairs)
    estate_all = _summarize(versions_for_namespaces(all_leaves))

    ecosystems = sorted(
        {_ecosystem(name) for pairs in leaf_pairs.values() for name, _ver in pairs}
    )

    def eco_filter(
        versions_by_pkg: dict[str, set[str]], ecosystem: str
    ) -> dict[str, set[str]]:
        if ecosystem == "all":
            return versions_by_pkg
        return {
            n: vs for n, vs in versions_by_pkg.items() if _ecosystem(n) == ecosystem
        }

    def grid_for(nss: set[str]) -> dict[str, dict[str, dict[str, Any]]]:
        base = versions_for_namespaces(nss)
        grid: dict[str, dict[str, dict[str, Any]]] = {"all": {"all": _summarize(base)}}
        for eco in ecosystems:
            filtered = eco_filter(base, eco)
            grid[eco] = {"all": _summarize(filtered)}
        return grid

    per_path: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for path in path_options:
        if path == "all":
            nss = all_leaves
        else:
            nss = {ns for ns in all_leaves if ns == path or ns.startswith(path + ".")}
        per_path[path] = grid_for(nss)

    per_tag: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for tag, nss in tag_namespaces.items():
        # UUID-set parity: only leaves that actually hold tagged projects
        scoped = nss & all_leaves
        if not scoped:
            continue
        per_tag[tag] = grid_for(scoped)

    return {
        "histKeys": list(HIST_KEYS),
        "ecosystems": ecosystems,
        "estate": per_path.get("all", {"all": {"all": estate_all}}),
        "perPath": per_path,
        "perTag": per_tag,
    }
