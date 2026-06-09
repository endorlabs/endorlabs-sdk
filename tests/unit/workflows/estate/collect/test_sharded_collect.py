"""Tests for sharded parallel list collection."""

from __future__ import annotations

import threading
import time
from unittest.mock import Mock

from endorlabs.workflows.estate.collect.shards import (
    ParentShard,
    parallel_map_shards,
    project_dict_to_shard,
    project_model_to_shard,
    resolve_worker_count,
)


def test_resolve_worker_count_caps_to_shards() -> None:
    assert resolve_worker_count(16, 0) == 1
    assert resolve_worker_count(16, 5) == 5
    assert resolve_worker_count(3, 10) == 3


def test_project_dict_to_shard_uses_tenant_meta_namespace() -> None:
    shard = project_dict_to_shard(
        {
            "uuid": "p1",
            "meta": {"name": "repo-a"},
            "tenant_meta": {"namespace": "tenant.child"},
        },
        "tenant",
    )
    assert shard.key == "p1"
    assert shard.namespace == "tenant.child"
    assert shard.label == "repo-a"


def test_project_model_to_shard_fallback_namespace() -> None:
    project = Mock(uuid="p2", tenant_meta=None, meta=None)
    shard = project_model_to_shard(project, "tenant.root")
    assert shard.key == "p2"
    assert shard.namespace == "tenant.root"


def test_parallel_map_shards_runs_all_shards() -> None:
    shards = [ParentShard(key=str(i), namespace="ns", label=f"p{i}") for i in range(4)]
    seen: list[str] = []
    lock = threading.Lock()

    def _work(shard: ParentShard) -> str:
        time.sleep(0.01)
        with lock:
            seen.append(shard.key)
        return shard.key

    results = parallel_map_shards(
        shards,
        _work,
        max_workers=2,
        progress_label="test shards",
        progress_every=2,
    )
    assert sorted(results) == ["0", "1", "2", "3"]
    assert sorted(seen) == ["0", "1", "2", "3"]


def test_parallel_map_shards_empty() -> None:
    assert (
        parallel_map_shards([], lambda s: s.key, max_workers=4, progress_label="x")
        == []
    )
