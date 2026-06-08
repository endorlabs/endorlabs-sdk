"""Reusable parallel collection keyed by project / parent shard."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, TypeVar

from endorlabs.workflows.list_bounds import format_progress

LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


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


def parallel_map_shards(
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
                LOGGER.info(format_progress(progress_label, completed, total))
    return results
