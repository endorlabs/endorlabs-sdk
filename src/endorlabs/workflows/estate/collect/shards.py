"""Reusable parallel collection keyed by project / parent shard.

Deprecated import path: prefer ``endorlabs.tools.list_sharding``.
"""

from __future__ import annotations

from endorlabs.tools.list_sharding import (
    ParentShard,
    list_for_shards,
    parallel_map_shards,
    project_dict_to_shard,
    project_model_to_shard,
    resolve_worker_count,
)

__all__ = [
    "ParentShard",
    "list_for_shards",
    "parallel_map_shards",
    "project_dict_to_shard",
    "project_model_to_shard",
    "resolve_worker_count",
]
