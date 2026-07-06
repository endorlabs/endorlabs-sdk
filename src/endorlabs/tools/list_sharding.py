"""Parallel list helpers keyed by project shard."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any

from endorlabs.tools.parallel_scopes import parallel_over
from endorlabs.utils.logging_config import get_resource_logger

LOGGER = get_resource_logger(__name__)


@dataclass(frozen=True, slots=True)
class ProjectShard:
    """One parallel list shard (project UUID + wire namespace)."""

    project_uuid: str
    namespace: str
    label: str | None = None


def project_dict_to_shard(project: dict[str, Any], fallback_ns: str) -> ProjectShard:
    """Build a shard from an API-style project dict."""
    uuid = str(project.get("uuid") or "")
    ns = (project.get("tenant_meta") or {}).get("namespace") or fallback_ns
    name = (project.get("meta") or {}).get("name")
    label = str(name) if name else None
    return ProjectShard(project_uuid=uuid, namespace=str(ns), label=label)


PROJECT_UUID_FILTER_FIELD = "spec.project_uuid"


def project_scoped_filter(base_filter: str, project_uuid: str) -> str:
    """Append a project UUID clause for per-project list shards."""
    clause = f'{PROJECT_UUID_FILTER_FIELD}=="{project_uuid}"'
    return f"{base_filter} and {clause}" if base_filter else clause


def single_shard_namespace(shards: Sequence[ProjectShard]) -> str | None:
    """Return the sole namespace when every shard shares one path segment."""
    namespaces = {shard.namespace for shard in shards}
    if len(namespaces) == 1:
        return next(iter(namespaces))
    return None


def project_model_to_shard(project: Any, fallback_ns: str) -> ProjectShard:
    """Build a shard from an SDK Project model."""
    uuid = str(getattr(project, "uuid", None) or "")
    tenant_meta = getattr(project, "tenant_meta", None)
    ns = getattr(tenant_meta, "namespace", None) if tenant_meta else None
    namespace = str(ns) if ns else fallback_ns
    meta = getattr(project, "meta", None)
    name = getattr(meta, "name", None) if meta else None
    label = str(name) if name else None
    return ProjectShard(project_uuid=uuid, namespace=namespace, label=label)


def topology_to_project_shards(
    topology: Any, *, fallback_ns: str
) -> list[ProjectShard]:
    """Build list shards from a :class:`~endorlabs.query.TopologySnapshot`."""
    projects = getattr(topology, "projects", None)
    if not projects:
        return []
    shards: list[ProjectShard] = []
    for proj in projects:
        if isinstance(proj, dict):
            shards.append(project_dict_to_shard(proj, fallback_ns))
            continue
        uuid = str(getattr(proj, "uuid", None) or "")
        if not uuid:
            continue
        ns = getattr(proj, "namespace", None)
        if not ns:
            tenant_meta = getattr(proj, "tenant_meta", None)
            ns = getattr(tenant_meta, "namespace", None) if tenant_meta else None
        namespace = str(ns) if ns else fallback_ns
        name = getattr(proj, "name", None)
        if name is None:
            meta = getattr(proj, "meta", None)
            name = getattr(meta, "name", None) if meta else None
        label = str(name) if name else None
        shards.append(ProjectShard(project_uuid=uuid, namespace=namespace, label=label))
    return shards


def resolve_worker_count(max_workers: int, shard_count: int) -> int:
    """Cap worker pool size to shard count (minimum 1)."""
    return max(1, min(max_workers, shard_count or 1))


def parallel_map_shards_iter[T](
    shards: Sequence[ProjectShard],
    fn: Callable[[ProjectShard], T],
    *,
    max_workers: int,
    progress_label: str,
    progress_every: int = 50,
    on_progress: Callable[[int, int], None] | None = None,
) -> Iterator[T]:
    """Run ``fn`` per shard; yield each result as its worker completes."""
    if not shards:
        return

    completed = 0
    total = len(shards)

    def _on_result(_: T) -> None:
        nonlocal completed
        completed += 1
        if on_progress is not None:
            on_progress(completed, total)
        elif completed % progress_every == 0 or completed == total:
            LOGGER.info("%s: %s/%s", progress_label, completed, total)

    yield from parallel_over(
        shards,
        fn,
        max_workers=max_workers,
        on_result=_on_result,
    )


def parallel_map_shards[T](
    shards: Sequence[ProjectShard],
    fn: Callable[[ProjectShard], T],
    *,
    max_workers: int,
    progress_label: str,
    progress_every: int = 50,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[T]:
    """Run ``fn`` per shard in a thread pool; results in completion order."""
    return list(
        parallel_map_shards_iter(
            shards,
            fn,
            max_workers=max_workers,
            progress_label=progress_label,
            progress_every=progress_every,
            on_progress=on_progress,
        )
    )


def list_for_shards(
    facade: Any,
    shards: Sequence[ProjectShard],
    filter_fn: Callable[[ProjectShard], str],
    *,
    max_workers: int = 10,
    **list_kwargs: Any,
) -> list[Any]:
    """List resources per shard in parallel and return a flat concatenated result."""
    rows: list[Any] = []

    def _worker(shard: ProjectShard) -> list[Any]:
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
