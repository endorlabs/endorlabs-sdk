"""Tenant-wide PRF finding collection and aggregation helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

from endorlabs.tools.list_sharding import (
    ProjectShard,
    parallel_map_shards,
    single_shard_namespace,
)
from endorlabs.workflows.wire_access import (
    dict_str,
    model_to_dict,
    nested_dict,
    nested_str,
)

if TYPE_CHECKING:
    from endorlabs import Client

ECOSYSTEMS = ("NUGET", "NPM", "MAVEN", "PYPI")
ECO_ENUM = {
    "NUGET": "ECOSYSTEM_NUGET",
    "NPM": "ECOSYSTEM_NPM",
    "MAVEN": "ECOSYSTEM_MAVEN",
    "PYPI": "ECOSYSTEM_PYPI",
}
ECO_LABEL = {
    "NUGET": "NuGet",
    "NPM": "NPM",
    "MAVEN": "Maven",
    "PYPI": "PyPI",
}
ENUM_TO_ECO = {value: key for key, value in ECO_ENUM.items()}

PRF_AGG_MASK = (
    "meta.parent_uuid,tenant_meta.namespace,"
    "spec.ecosystem,spec.approximation,spec.finding_tags"
)
PRD_LIST_MASK = "meta.parent_uuid,tenant_meta.namespace,spec.ecosystem"
PRD_TAG = "FINDING_TAGS_POTENTIALLY_REACHABLE_DEPENDENCY"
PV_HYDRATION_MASK = "uuid,spec.resolution_errors,spec.precomputed_call_graph_state"
PV_BATCH_SIZE = 50


def finding_row_to_dict(finding: Any) -> dict[str, Any]:
    """Normalize a masked Finding list row to a dict."""
    return model_to_dict(finding)


def pv_row_to_dict(pv: Any) -> dict[str, Any]:
    """Normalize a masked PackageVersion list row to a dict."""
    return model_to_dict(pv)


def findings_by_parent(findings: list[dict[str, Any]]) -> Counter[str]:
    """Count findings per ``meta.parent_uuid``."""
    counts: Counter[str] = Counter()
    for finding in findings:
        parent_uuid = nested_str(nested_dict(finding, "meta"), "parent_uuid")
        if parent_uuid:
            counts[parent_uuid] += 1
    return counts


def _eco_key(ecosystem: str | None) -> str | None:
    if not ecosystem:
        return None
    return ENUM_TO_ECO.get(str(ecosystem))


def _is_approximated(spec: dict[str, Any]) -> bool | None:
    value = spec.get("approximation")
    if value is True:
        return True
    if value is False:
        return False
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return None


def _has_prd_tag(spec: dict[str, Any]) -> bool:
    tags_raw = spec.get("finding_tags")
    if isinstance(tags_raw, str):
        return PRD_TAG in tags_raw
    if isinstance(tags_raw, list):
        return PRD_TAG in [str(tag) for tag in cast("list[Any]", tags_raw)]
    return False


def aggregate_prf_metrics(
    findings: list[dict[str, Any]],
) -> tuple[dict[str, int], dict[str, int], dict[str, int], dict[str, int]]:
    """Derive per-ecosystem PRF, approximation, and PRD counts from listed rows."""
    prf_counts: dict[str, int] = defaultdict(int)
    approx_counts: dict[str, int] = defaultdict(int)
    not_approx_counts: dict[str, int] = defaultdict(int)
    prd_counts: dict[str, int] = defaultdict(int)

    for finding in findings:
        spec = nested_dict(finding, "spec")
        eco = _eco_key(spec.get("ecosystem"))
        if eco is None:
            continue
        prf_counts[eco] += 1
        approximated = _is_approximated(spec)
        if approximated is True:
            approx_counts[eco] += 1
        elif approximated is False:
            not_approx_counts[eco] += 1
        if _has_prd_tag(spec):
            prd_counts[eco] += 1

    return (
        dict(prf_counts),
        dict(approx_counts),
        dict(not_approx_counts),
        dict(prd_counts),
    )


def parent_uuids_by_eco(findings: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Map ecosystem key to unique PRF parent PackageVersion UUIDs."""
    out: dict[str, set[str]] = defaultdict(set)
    for finding in findings:
        spec = nested_dict(finding, "spec")
        eco = _eco_key(spec.get("ecosystem"))
        parent_uuid = nested_str(nested_dict(finding, "meta"), "parent_uuid")
        if eco is None or not parent_uuid:
            continue
        out[eco].add(parent_uuid)
    return out


def parent_uuids_by_namespace(
    findings: Sequence[dict[str, Any]],
    parent_uuids: set[str],
) -> tuple[dict[str, set[str]], set[str]]:
    """Group parent PV UUIDs by finding ``tenant_meta.namespace``."""
    by_namespace: dict[str, set[str]] = defaultdict(set)
    for finding in findings:
        parent_uuid = nested_str(nested_dict(finding, "meta"), "parent_uuid")
        if not parent_uuid:
            continue
        parent_key = parent_uuid
        if parent_key not in parent_uuids:
            continue
        namespace = nested_str(nested_dict(finding, "tenant_meta"), "namespace")
        if namespace:
            by_namespace[namespace].add(parent_key)
    assigned = {uuid for uuids in by_namespace.values() for uuid in uuids}
    return dict(by_namespace), parent_uuids - assigned


def list_findings_sharded(
    client: Client,
    shards: Sequence[ProjectShard],
    filt: str,
    *,
    mask: str,
    max_pages: int | None = None,
    max_workers: int = 12,
    progress_label: str = "Finding shards",
) -> list[dict[str, Any]]:
    """List findings per project in parallel (``spec.project_uuid`` + namespace)."""
    if not shards:
        return []

    list_kwargs: dict[str, Any] = {
        "mask": mask,
    }
    if max_pages is not None:
        list_kwargs["max_pages"] = max_pages

    def _worker(shard: ProjectShard) -> list[dict[str, Any]]:
        # Prefer generated accessor (spec.project_uuid + source namespace).
        project = SimpleNamespace(
            uuid=shard.project_uuid,
            namespace=shard.namespace,
            tenant_meta=SimpleNamespace(namespace=shard.namespace),
        )
        rows = client.Finding.list_by_project(
            project,
            filter=filt,
            **list_kwargs,
        )
        return [finding_row_to_dict(row) for row in rows]

    batches = parallel_map_shards(
        shards,
        _worker,
        max_workers=max_workers,
        progress_label=progress_label,
    )
    return [row for batch in batches for row in batch]


def _list_findings_scope(
    client: Client,
    namespace: str,
    filt: str,
    *,
    mask: str,
    max_pages: int | None,
    traverse: bool,
) -> list[dict[str, Any]]:
    list_kwargs: dict[str, Any] = {
        "filter": filt,
        "mask": mask,
    }
    if max_pages is not None:
        list_kwargs["max_pages"] = max_pages
    return [
        finding_row_to_dict(row)
        for row in client.Finding.list_iter(
            namespace=namespace,
            traverse=traverse,
            **list_kwargs,
        )
    ]


def list_findings_tenant(
    client: Client,
    tenant: str,
    filt: str,
    *,
    mask: str,
    max_pages: int | None = None,
    max_workers: int = 12,
    max_project_pages: int | None = None,
    shards: Sequence[ProjectShard] | None = None,
) -> list[dict[str, Any]]:
    """List findings tenant-wide via per-project parallel queries.

    Discovers project shards once (or reuses *shards*). When every project
    shares one namespace path, uses a single ``traverse=True`` query instead
    of N duplicate namespace lists. Otherwise lists per project with
    ``spec.project_uuid`` scoping.
    """
    project_shards = (
        list(shards)
        if shards is not None
        else client.Query.Project.discover(
            tenant,
            traverse=True,
            max_pages=max_project_pages,
            exclude_sbom=True,
        ).project_shards()
    )
    if not project_shards:
        return []

    shared_namespace = single_shard_namespace(project_shards)
    if shared_namespace is not None and len(project_shards) > 1:
        return _list_findings_scope(
            client,
            shared_namespace,
            filt,
            mask=mask,
            max_pages=max_pages,
            traverse=True,
        )

    return list_findings_sharded(
        client,
        project_shards,
        filt,
        mask=mask,
        max_pages=max_pages,
        max_workers=max_workers,
    )


def _fetch_pv_batch(
    client: Client,
    *,
    namespace: str,
    uuids: list[str],
    pv_filter: str,
    traverse: bool,
) -> list[dict[str, Any]]:
    if not uuids:
        return []
    quoted = ", ".join(f'"{uuid}"' for uuid in uuids)
    filt = f"{pv_filter} and uuid in [{quoted}]"
    rows = client.PackageVersion.list_iter(
        namespace=namespace,
        traverse=traverse,
        filter=filt,
        mask=PV_HYDRATION_MASK,
        page_size=100,
    )
    return [pv_row_to_dict(row) for row in rows]


def fetch_parent_package_versions(
    client: Client,
    tenant: str,
    prf_findings: Sequence[dict[str, Any]],
    parent_uuids: set[str],
    *,
    pv_filter: str,
    batch_size: int = PV_BATCH_SIZE,
) -> dict[str, dict[str, Any]]:
    """Hydrate parent PackageVersions grouped by project namespace."""
    by_namespace, orphan_uuids = parent_uuids_by_namespace(prf_findings, parent_uuids)
    pv_by_uuid: dict[str, dict[str, Any]] = {}

    for namespace, uuids in by_namespace.items():
        sorted_uuids = sorted(uuids)
        for idx in range(0, len(sorted_uuids), batch_size):
            batch = sorted_uuids[idx : idx + batch_size]
            for pv in _fetch_pv_batch(
                client,
                namespace=namespace,
                uuids=batch,
                pv_filter=pv_filter,
                traverse=False,
            ):
                uuid = dict_str(pv, "uuid")
                if uuid:
                    pv_by_uuid[uuid] = pv

    if orphan_uuids:
        sorted_orphans = sorted(orphan_uuids)
        for idx in range(0, len(sorted_orphans), batch_size):
            batch = sorted_orphans[idx : idx + batch_size]
            for pv in _fetch_pv_batch(
                client,
                namespace=tenant,
                uuids=batch,
                pv_filter=pv_filter,
                traverse=True,
            ):
                uuid = dict_str(pv, "uuid")
                if uuid and uuid not in pv_by_uuid:
                    pv_by_uuid[uuid] = pv

    return pv_by_uuid
