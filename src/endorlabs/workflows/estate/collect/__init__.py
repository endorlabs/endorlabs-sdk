"""Estate collect primitives."""

from __future__ import annotations

from endorlabs.tools.list_sharding import (
    ParentShard,
    parallel_map_shards,
    project_dict_to_shard,
    project_model_to_shard,
    resolve_worker_count,
)

from .bounds import (
    count_for_progress,
    count_list_delta_check,
    format_progress,
    is_list_truncated,
    list_row_capacity,
    resolve_max_pages,
    truncation_message,
)
from .dependency_metadata import (
    aggregate_consumers_by_version,
    aggregate_usage_by_package_version,
    dep_data_from_record,
    dependency_metadata_record_from_row,
    load_dependency_metadata_records,
)
from .runner import CollectResult, collect_workspace

__all__ = [
    "CollectResult",
    "ParentShard",
    "aggregate_consumers_by_version",
    "aggregate_usage_by_package_version",
    "collect_workspace",
    "count_for_progress",
    "count_list_delta_check",
    "dep_data_from_record",
    "dependency_metadata_record_from_row",
    "format_progress",
    "is_list_truncated",
    "list_row_capacity",
    "load_dependency_metadata_records",
    "parallel_map_shards",
    "project_dict_to_shard",
    "project_model_to_shard",
    "resolve_max_pages",
    "resolve_worker_count",
    "truncation_message",
]
