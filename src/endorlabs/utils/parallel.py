"""Parallel execution utilities for concurrent namespace queries.

This module provides utilities for executing list operations concurrently
across multiple namespaces, improving performance for large datasets.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypeVar

from .logging_config import get_resource_logger

logger = get_resource_logger(__name__)

T = TypeVar("T")


class ConcurrentNamespaceQueryError(RuntimeError):
    """Raised when one or more concurrent namespace queries fail."""

    def __init__(self, failures: list[tuple[str, Exception]]) -> None:
        self.failures = failures
        self.failed_namespaces = [namespace for namespace, _ in failures]
        details = "; ".join(
            f"{namespace}: {type(error).__name__}({error})"
            for namespace, error in failures
        )
        super().__init__(
            "Concurrent namespace query failed for "
            f"{len(failures)} namespace(s): {details}"
        )


def execute_across_namespaces(
    namespaces: list[str],
    query_fn: Callable[[str], list[T]],
    max_workers: int = 10,
) -> list[T]:
    """Execute query_fn concurrently across namespaces and merge results.

    This function queries each namespace in parallel using a thread pool,
    then merges all results into a single list. Any namespace failure raises
    ``ConcurrentNamespaceQueryError`` after all submitted queries complete.

    Args:
        namespaces: List of namespace strings to query.
        query_fn: Function that takes a namespace string and returns a list
            of resources. Will be called once per namespace.
        max_workers: Maximum number of concurrent threads. Defaults to 10.
            Higher values may hit API rate limits.

    Returns:
        Merged list of all results from all namespaces. Order is not guaranteed
        due to concurrent execution.

    Raises:
        ConcurrentNamespaceQueryError: One or more namespace queries failed.

    Example:
        >>> def query_findings(ns: str) -> list[Finding]:
        ...     return client.Finding.list(namespace=ns)
        >>> all_findings = execute_across_namespaces(
        ...     namespaces=["tenant.ns1", "tenant.ns2"],
        ...     query_fn=query_findings,
        ...     max_workers=5,
        ... )

    """
    if not namespaces:
        return []

    all_results: list[T] = []
    errors: list[tuple[str, Exception]] = []

    # Use min of max_workers and namespace count to avoid idle threads
    effective_workers = min(max_workers, len(namespaces))

    logger.info(
        "Starting concurrent queries across %d namespaces with %d workers",
        len(namespaces),
        effective_workers,
    )

    with ThreadPoolExecutor(max_workers=effective_workers) as executor:
        # Submit all tasks
        future_to_namespace = {executor.submit(query_fn, ns): ns for ns in namespaces}

        # Collect results as they complete
        for future in as_completed(future_to_namespace):
            ns = future_to_namespace[future]
            try:
                results = future.result()
                all_results.extend(results)
                logger.debug(
                    "Namespace %s returned %d results",
                    ns,
                    len(results),
                )
            except Exception as e:
                # Log error but continue with other namespaces
                logger.warning(
                    "Unable to query namespace '%s': %s",
                    ns,
                    e,
                )
                errors.append((ns, e))

    if errors:
        logger.error(
            "Concurrent query failed with %d errors out of %d namespaces",
            len(errors),
            len(namespaces),
        )
        raise ConcurrentNamespaceQueryError(errors)

    logger.info(
        "Concurrent query completed: %d total results from %d namespaces",
        len(all_results),
        len(namespaces),
    )

    return all_results
