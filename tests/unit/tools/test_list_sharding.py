"""Tests for list sharding helpers."""

from __future__ import annotations

from endorlabs.tools.list_sharding import (
    ParentShard,
    parallel_map_shards_iter,
    project_scoped_filter,
    single_shard_namespace,
)


def test_project_scoped_filter_appends_uuid_clause() -> None:
    filt = project_scoped_filter(
        "context.type==CONTEXT_TYPE_MAIN",
        "proj-1",
    )
    assert filt == ('context.type==CONTEXT_TYPE_MAIN and spec.project_uuid=="proj-1"')


def test_single_shard_namespace_detects_shared_path() -> None:
    shards = [
        ParentShard(key="a", namespace="tenant.child"),
        ParentShard(key="b", namespace="tenant.child"),
    ]
    assert single_shard_namespace(shards) == "tenant.child"


def test_single_shard_namespace_returns_none_when_paths_differ() -> None:
    shards = [
        ParentShard(key="a", namespace="tenant.child-a"),
        ParentShard(key="b", namespace="tenant.child-b"),
    ]
    assert single_shard_namespace(shards) is None


def test_parallel_map_shards_iter_yields_before_all_complete() -> None:
    import threading

    release_slow = threading.Event()
    yielded_before_slow_done: list[bool] = []

    shards = [
        ParentShard(key="slow", namespace="ns"),
        ParentShard(key="fast-a", namespace="ns"),
        ParentShard(key="fast-b", namespace="ns"),
    ]

    def _worker(shard: ParentShard) -> str:
        if shard.key == "slow":
            release_slow.wait(timeout=5.0)
        return shard.key

    for result in parallel_map_shards_iter(
        shards,
        _worker,
        max_workers=3,
        progress_label="iter test",
    ):
        yielded_before_slow_done.append(not release_slow.is_set())
        if result in {"fast-a", "fast-b"}:
            release_slow.set()

    assert True in yielded_before_slow_done
    assert len(yielded_before_slow_done) == 3
