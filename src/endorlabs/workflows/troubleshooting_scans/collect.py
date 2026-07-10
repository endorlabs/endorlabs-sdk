"""Project matching and parallel collect helpers for troubleshooting scans."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from endorlabs.workflows.wire_access import dict_str, nested_str


def match_projects(
    projects: list[dict[str, Any]],
    *,
    project_uuid: str | None,
    project_name: str | None,
    project_url: str | None,
    project_name_regex: str | None,
) -> list[dict[str, Any]]:
    """Apply project selection filters."""
    regex = (
        re.compile(project_name_regex, re.IGNORECASE) if project_name_regex else None
    )
    selected: list[dict[str, Any]] = []
    for project in projects:
        uuid = dict_str(project, "uuid")
        name = nested_str(project, "meta", "name")
        if project_uuid and uuid != project_uuid:
            continue
        if project_name and project_name.lower() not in str(name).lower():
            continue
        if project_url and project_url.lower() not in str(name).lower():
            continue
        if regex and not regex.search(str(name)):
            continue
        selected.append(project)
    return selected


def parallel_collect_for_projects(
    projects: Sequence[dict[str, Any]],
    fetch_fn: Callable[[Any], Iterable[Any]],
    *,
    max_workers: int,
    fallback_ns: str,
    progress_label: str,
    progress_every: int = 50,
) -> list[Any]:
    """Parallel per-project fetch; flatten iterable results from each shard."""
    from endorlabs.tools.list_sharding import (
        parallel_map_shards,
        project_dict_to_shard,
    )

    shards = [
        project_dict_to_shard(project, fallback_ns)
        for project in projects
        if dict_str(project, "uuid")
    ]
    per_shard = parallel_map_shards(
        shards,
        fetch_fn,
        max_workers=max_workers,
        progress_label=progress_label,
        progress_every=progress_every,
    )
    out: list[Any] = []
    for batch in per_shard:
        out.extend(batch)
    return out
