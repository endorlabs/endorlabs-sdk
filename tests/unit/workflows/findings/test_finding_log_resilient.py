"""Unit tests for FindingLog resilient group_by_time escalate."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from endorlabs.core.exceptions import NetworkError, ServerError
from endorlabs.tools.list_sharding import ProjectShard
from endorlabs.workflows.findings.finding_log_trends import (
    query_operation_group_counts_resilient,
)


def test_resilient_returns_empty_for_empty_parent_uuids() -> None:
    client = MagicMock()
    counts = query_operation_group_counts_resilient(
        client,
        namespace="example-tenant",
        base_filter="meta.create_time>=date(2026-01-01T00:00:00Z)",
        operation="CREATE",
        level="CRITICAL",
        interval="week",
        parent_uuids=[],
    )
    assert counts == {}
    client.FindingLog.list_groups.assert_not_called()


def test_resilient_single_project_does_not_discover_on_timeout() -> None:
    client = MagicMock()

    def list_groups(**_kwargs: object) -> list[object]:
        raise ServerError("timeout", status_code=504)

    client.FindingLog.list_groups = list_groups

    try:
        query_operation_group_counts_resilient(
            client,
            namespace="example-tenant.child",
            base_filter="meta.create_time>=date(2026-01-01T00:00:00Z)",
            operation="CREATE",
            level="HIGH",
            interval="week",
            parent_uuids=["proj-1"],
        )
    except ServerError:
        pass
    else:
        raise AssertionError("expected ServerError to propagate for single project")
    client.Query.Project.discover.assert_not_called()


def test_resilient_leaf_scope_escalates_to_shards_on_timeout() -> None:
    client = MagicMock()
    calls = {"n": 0}
    filters: list[str] = []

    def list_groups(**kwargs: object) -> list[object]:
        calls["n"] += 1
        filt = ""
        lp = kwargs.get("list_params")
        if lp is not None:
            filt = str(getattr(lp, "filter", "") or "")
        if not filt:
            filt = str(kwargs.get("filter") or "")
        filters.append(filt)
        if calls["n"] == 1:
            raise ServerError("timeout", status_code=504)
        return []

    client.FindingLog.list_groups = list_groups
    client.Query.Project.discover.return_value = SimpleNamespace(
        project_shards=lambda: [
            ProjectShard(
                project_uuid="p-1",
                namespace="example-tenant.child",
                label="child",
            ),
        ]
    )

    counts = query_operation_group_counts_resilient(
        client,
        namespace="example-tenant.child",
        base_filter="meta.create_time>=date(2026-01-01T00:00:00Z)",
        operation="CREATE",
        level="CRITICAL",
        interval="week",
        parent_uuids=None,
        max_workers=2,
    )
    assert counts == {}
    assert calls["n"] >= 2
    client.Query.Project.discover.assert_called_once()
    shard_filters = [f for f in filters[1:] if f]
    assert shard_filters
    assert all("meta.parent_uuid" in f for f in shard_filters)
    assert all("spec.project_uuid" not in f for f in shard_filters)


def test_resilient_shard_timeout_returns_empty_counts() -> None:
    """Per-project shard timeouts should not abort the whole escalate merge."""
    client = MagicMock()
    calls = {"n": 0}

    def list_groups(**_kwargs: object) -> list[object]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise ServerError("timeout", status_code=504)
        raise NetworkError(
            "Network error after 2 attempt(s): The read operation timed out"
        )

    client.FindingLog.list_groups = list_groups
    client.Query.Project.discover.return_value = SimpleNamespace(
        project_shards=lambda: [
            ProjectShard(
                project_uuid="p-1",
                namespace="example-tenant.child",
                label="child",
            ),
        ]
    )

    counts = query_operation_group_counts_resilient(
        client,
        namespace="example-tenant.child",
        base_filter="meta.create_time>=date(2026-01-01T00:00:00Z)",
        operation="CREATE",
        level="CRITICAL",
        interval="week",
        parent_uuids=None,
        max_workers=2,
    )
    assert counts == {}
    assert calls["n"] >= 2
