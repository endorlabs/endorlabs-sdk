"""Generic ``list_groups`` + ``group_by_time`` bucket helpers for log resources."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from endorlabs.core.types import ListParameters
from endorlabs.operations.list_response import (
    GroupBucket,
    buckets_to_counts,
    group_bucket_count,
    group_bucket_time_key,
    parse_bucket_key,
)

ListGroupsFn = Callable[..., Iterable[GroupBucket]]

__all__ = [
    "ListGroupsFn",
    "buckets_to_counts",
    "group_bucket_count",
    "group_bucket_time_key",
    "group_by_time_counts",
    "is_timeout_like",
    "parse_bucket_key",
]


def is_timeout_like(exc: BaseException) -> bool:
    """Return whether *exc* looks like a gateway or client read timeout."""
    from endorlabs.core.exceptions import NetworkError, ServerError

    if isinstance(exc, ServerError) and exc.status_code == 504:
        return True
    if isinstance(exc, NetworkError):
        msg = str(exc).lower()
        return "timeout" in msg or "deadline" in msg
    msg = str(exc).lower()
    return "deadline" in msg or "504" in msg


def group_by_time_counts(
    list_groups: ListGroupsFn,
    *,
    namespace: str,
    filter: str,
    traverse: bool = True,
    interval: str = "week",
    time_path: str = "meta.create_time",
) -> dict[str, int]:
    """Run one aggregated ``list_groups`` query and return time-bucket counts."""
    list_params = ListParameters(
        group_by_time=True,
        group_aggregation_paths=[time_path],
        group_by_time_interval=interval,
        group_by_time_mode="count",
        filter=filter,
        traverse=traverse,
    )
    buckets = list(
        list_groups(
            namespace=namespace,
            traverse=traverse,
            filter=filter,
            list_params=list_params,
        )
    )
    return buckets_to_counts(buckets, time_path=time_path)
