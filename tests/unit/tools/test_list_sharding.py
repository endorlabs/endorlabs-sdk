"""Tests for list sharding helpers."""

from __future__ import annotations

from endorlabs.tools.list_sharding import (
    ParentShard,
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
