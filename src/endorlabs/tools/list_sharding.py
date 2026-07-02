"""Parallel list helpers keyed by project or parent shard."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from endorlabs.utils.logging_config import get_resource_logger

LOGGER = get_resource_logger(__name__)


@dataclass(frozen=True, slots=True)
class ParentShard:
    """One parallel list shard (project UUID or parent key + namespace)."""

    key: str
    namespace: str
    label: str | None = None


def project_dict_to_shard(project: dict[str, Any], fallback_ns: str) -> ParentShard:
    """Build a shard from an API-style project dict."""
    uuid = str(project.get("uuid") or "")
    ns = (project.get("tenant_meta") or {}).get("namespace") or fallback_ns
    name = (project.get("meta") or {}).get("name")
    label = str(name) if name else None
    return ParentShard(key=uuid, namespace=str(ns), label=label)


PROJECT_UUID_FILTER_FIELD = "spec.project_uuid"


def project_scoped_filter(base_filter: str, project_uuid: str) -> str:
    """Append a project UUID clause for per-project list shards."""
    clause = f'{PROJECT_UUID_FILTER_FIELD}=="{project_uuid}"'
    return f"{base_filter} and {clause}" if base_filter else clause


def single_shard_namespace(shards: Sequence[ParentShard]) -> str | None:
    """Return the sole namespace when every shard shares one path segment."""
    namespaces = {shard.namespace for shard in shards}
    if len(namespaces) == 1:
        return next(iter(namespaces))
    return None


def project_model_to_shard(project: Any, fallback_ns: str) -> ParentShard:
    """Build a shard from an SDK Project model."""
    uuid = str(getattr(project, "uuid", None) or "")
    tenant_meta = getattr(project, "tenant_meta", None)
    ns = getattr(tenant_meta, "namespace", None) if tenant_meta else None
    namespace = str(ns) if ns else fallback_ns
    meta = getattr(project, "meta", None)
    name = getattr(meta, "name", None) if meta else None
    label = str(name) if name else None
    return ParentShard(key=uuid, namespace=namespace, label=label)


def resolve_worker_count(max_workers: int, shard_count: int) -> int:
    """Cap worker pool size to shard count (minimum 1)."""
    return max(1, min(max_workers, shard_count or 1))


def parallel_map_shards[T](
    shards: Sequence[ParentShard],
    fn: Callable[[ParentShard], T],
    *,
    max_workers: int,
    progress_label: str,
    progress_every: int = 50,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[T]:
    """Run ``fn`` per shard in a thread pool; results in completion order."""
    if not shards:
        return []
    workers = resolve_worker_count(max_workers, len(shards))
    results: list[T] = []
    completed = 0
    total = len(shards)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fn, shard): shard for shard in shards}
        for fut in as_completed(futures):
            results.append(fut.result())
            completed += 1
            if on_progress is not None:
                on_progress(completed, total)
            elif completed % progress_every == 0 or completed == total:
                LOGGER.info("%s: %s/%s", progress_label, completed, total)
    return results


def list_for_shards(
    facade: Any,
    shards: Sequence[ParentShard],
    filter_fn: Callable[[ParentShard], str],
    *,
    max_workers: int = 10,
    **list_kwargs: Any,
) -> list[Any]:
    """List resources per shard in parallel and return a flat concatenated result.

    Each shard calls ``facade.list`` with ``namespace=shard.namespace`` and a
    per-shard filter from ``filter_fn``. For project-keyed shards, include
    ``project_scoped_filter()`` (or ``Finding.list_by_project``) so rows are not
    duplicated when many projects share one namespace path.
    """
    rows: list[Any] = []

    def _worker(shard: ParentShard) -> list[Any]:
        filt = filter_fn(shard)
        batch = facade.list(namespace=shard.namespace, filter=filt, **list_kwargs)
        return list(batch or [])

    entry = getattr(facade, "_entry", None)
    if entry is not None:
        attr_name = getattr(entry, "attr_name", "resource")
    else:
        attr_name = "resource"
    for batch in parallel_map_shards(
        shards,
        _worker,
        max_workers=max_workers,
        progress_label=f"{attr_name} shards",
    ):
        rows.extend(batch)
    return rows
