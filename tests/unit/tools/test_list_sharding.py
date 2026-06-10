"""Tests for endorlabs.tools.list_sharding."""

from __future__ import annotations

from unittest.mock import Mock

from endorlabs.tools.list_sharding import (
    ParentShard,
    list_for_shards,
    parallel_map_shards,
)


def test_parallel_map_shards_invokes_each_shard() -> None:
    shards = [
        ParentShard(key="a", namespace="tenant.a"),
        ParentShard(key="b", namespace="tenant.b"),
    ]
    seen: list[str] = []

    def _fn(shard: ParentShard) -> str:
        seen.append(shard.key)
        return shard.key

    results = parallel_map_shards(
        shards,
        _fn,
        max_workers=2,
        progress_label="test",
    )
    assert sorted(results) == ["a", "b"]
    assert sorted(seen) == ["a", "b"]


def test_list_for_shards_passes_namespace_and_filter() -> None:
    facade = Mock()
    facade._entry = Mock(attr_name="Finding")
    facade.list = Mock(return_value=[{"uuid": "1"}])
    shards = [ParentShard(key="proj-1", namespace="tenant.child")]

    rows = list_for_shards(
        facade,
        shards,
        filter_fn=lambda s: f'spec.project_uuid=="{s.key}"',
        max_workers=1,
        max_pages=1,
    )

    assert rows == [{"uuid": "1"}]
    facade.list.assert_called_once_with(
        namespace="tenant.child",
        filter='spec.project_uuid=="proj-1"',
        max_pages=1,
    )
