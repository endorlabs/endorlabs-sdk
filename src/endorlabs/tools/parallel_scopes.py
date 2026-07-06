"""Shared parallel execution over scope-like units (list shards, query scopes)."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypeVar

T = TypeVar("T")
S = TypeVar("S")


def parallel_over[S, T](
    scopes: Sequence[S],
    fn: Callable[[S], T],
    *,
    max_workers: int,
    on_result: Callable[[T], None] | None = None,
) -> Iterator[T]:
    """Run ``fn(scope)`` per scope; yield each result as its worker completes."""
    if not scopes:
        return
    workers = max(1, min(max_workers, len(scopes)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fn, scope): scope for scope in scopes}
        for fut in as_completed(futures):
            result = fut.result()
            if on_result is not None:
                on_result(result)
            yield result
